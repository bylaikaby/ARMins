"""Isolated native Slicer integration check for ARMins.

Version: 0.7.1 (local/unreleased)
Last updated: 2026-10-22
Change history: CHANGELOG.md
Status: candidate

Test real MRML mirroring, source preservation, geometry, label identity,
save/reload and rejected overlapping parcels. The design phase captures the
actual dialog before the behavior phase runs.

Run with Slicer --testing --no-splash --python-script <this>. The behavior
phase needs Slicer's main-window layout manager; the design phase may also
use --no-main-window. Use a separate testing process and an isolated scene.
Required environment: ARMINS_TEST_OUTPUT (new/empty folder), ARMINS_TEMPLATE,
and ARMINS_ATLAS (registered local 3-D L6 input). Hierarchy phase additionally
requires ARMINS_HIERARCHY pointing to the external provider CSV. Optional:
ARMINS_TEST_PHASE ('design', 'behavior', or 'hierarchy'; default behavior),
ARMINS_OUTPUT_DIR.
"""

import hashlib
import json
import os
from pathlib import Path
import runpy
import traceback

import numpy as np
import slicer


def main():
    output = Path(os.environ['ARMINS_TEST_OUTPUT']).resolve()
    phase = os.environ.get('ARMINS_TEST_PHASE', 'behavior')
    loader = Path(os.environ.get('ARMINS_LOADER',
        str(Path(__file__).resolve().parents[1] / 'armins.py')))
    output.mkdir(parents=True, exist_ok=True)
    receipt_path = output / f'{phase}_receipt.json'
    if receipt_path.exists():
        raise FileExistsError(receipt_path)
    receipt = {'phase': phase, 'status': 'running', 'loader': str(loader),
        'loader_sha256': hashlib.sha256(loader.read_bytes()).hexdigest(),
        'slicer_version': slicer.app.applicationVersion, 'checks': []}

    def passed(label):
        receipt['checks'].append(label)
        print('PASS:', label, flush=True)

    try:
        ns = runpy.run_path(str(loader), run_name='armins_mirror_native_test')
        glob = ns['run'].__globals__
        if phase == 'design':
            main_window = slicer.util.mainWindow()
            main_style_before = main_window.styleSheet if main_window is not None else None
            dialog = ns['show_gui']()
            slicer.app.processEvents()
            import qt
            assert '#263746' in dialog.styleSheet and '#168a91' in dialog.styleSheet
            assert dialog.findChild(qt.QLabel, 'ARMinsBanner') is not None
            side = dialog.findChild(qt.QComboBox, 'WorkingHemisphere')
            direction = dialog.findChild(qt.QLabel, 'MirrorDirection')
            scene_before_side = slicer.mrmlScene.GetNumberOfNodes()
            side.setCurrentIndex(1)
            assert direction.text == 'R → L' and '#97521f' in direction.styleSheet
            assert slicer.mrmlScene.GetNumberOfNodes() == scene_before_side
            right_image = output / 'mirror_dialog_right.png'
            assert dialog.grab().save(str(right_image))
            receipt['right_side_screenshot'] = str(right_image)
            side.setCurrentIndex(0)
            assert direction.text == 'L → R' and '#126b78' in direction.styleSheet
            if main_window is not None:
                assert main_window.styleSheet == main_style_before
            passed('dialog-local VisPa palette and redundant L/R colour-direction cues leave scene and Slicer theme unchanged')
            use_region = dialog.findChild(qt.QPushButton, 'UseSelectedRegionButton')
            assert use_region.property('arminsRole') == 'region' and not use_region.enabled
            assert '#59416f' in dialog.styleSheet and '#334a59' in dialog.styleSheet
            search = dialog.findChild(qt.QLineEdit, 'ARMHierarchySearch')
            assert search.palette.color(qt.QPalette.Disabled, qt.QPalette.PlaceholderText).name() == '#334a59'
            passed('dark inactive text and placeholder; distinct purple region action retains disabled state')
            image_path = output / 'mirror_dialog.png'
            assert dialog.grab().save(str(image_path))
            receipt['screenshot'] = str(image_path)
            labels = [button.text for button in dialog.findChildren(qt.QPushButton)]
            assert any('Mirror selected side' in label for label in labels), labels
            assert any('Save mirrored candidate' in label for label in labels), labels
            setup_button = next(button for button in dialog.findChildren(qt.QPushButton)
                                if button.objectName == 'NMTv21SetupHelpButton')
            scene_count_before_help = slicer.mrmlScene.GetNumberOfNodes()
            setup_button.click()
            slicer.app.processEvents()
            help_dialog = dialog.findChild(qt.QDialog, 'NMTAtlasSetupHelpDialog')
            assert help_dialog is not None and help_dialog.isVisible()
            help_label = help_dialog.findChild(qt.QLabel, 'NMTAtlasSetupGuidance')
            assert all(url in help_label.text for url in (
                ns['NMT_ARCHIVE_URL'], ns['NMT_INSTALL_URL'], ns['ARMINS_ATLAS_SETUP_URL']))
            assert 'supplemental_ARM/ARM_6_in_NMT_v2.1_sym.nii.gz' in help_label.text
            assert 'prepare --level 6' in help_label.text
            assert 'Linux, macOS, or WSL' in help_label.text
            assert './atlas-data' in help_label.text
            command = help_dialog.findChild(qt.QLineEdit, 'NMTInstallCommand')
            assert command.text == ns['NMT_INSTALL_COMMAND']
            copy_button = help_dialog.findChild(qt.QPushButton, 'CopyNMTInstallCommandButton')
            clipboard = slicer.app.clipboard()
            previous_clipboard = clipboard.text
            if callable(previous_clipboard):
                previous_clipboard = previous_clipboard()
            try:
                copy_button.click()
                copied_command = clipboard.text
                if callable(copied_command):
                    copied_command = copied_command()
                assert copied_command == ns['NMT_INSTALL_COMMAND']
            finally:
                clipboard.setText(previous_clipboard)
            assert slicer.mrmlScene.GetNumberOfNodes() == scene_count_before_help
            help_image = output / 'atlas_setup_help.png'
            assert help_dialog.grab().save(str(help_image))
            receipt['atlas_setup_help_screenshot'] = str(help_image)
            passed('setup help opens without scene changes and exposes official links and copyable install command')
            help_dialog.findChild(qt.QPushButton, 'CloseNMTSetupHelpButton').click()
            slicer.app.processEvents()
            assert not help_dialog.isVisible()
            passed('native setup-help Close button accepts the Qt clicked signal and closes the dialog')
            receipt['buttons'] = labels
            passed('actual native dialog contains both mirror controls; screenshot saved')
            dialog.close()
        elif phase == 'hierarchy':
            import vtk
            hierarchy_path = Path(os.environ['ARMINS_HIERARCHY']).resolve()
            input_file_paths = [Path(glob['REF_PATH']).resolve(), Path(glob['ARM_PATH']).resolve(), hierarchy_path]
            original_input_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                     for path in input_file_paths}
            resolver_type, _ = glob['_load_hierarchy_class'](str(hierarchy_path))
            resolver = resolver_type.from_file(hierarchy_path)
            left_hit = next(hit for hit in resolver.search('CL_ACC', side='L', level=3)
                            if hit['abbreviation'] == 'CL_ACC')
            profile_l = resolver.profile_for(left_hit['index'], left_hit['level'], 'L',
                                             namespace=left_hit['namespace'])
            profile_r = resolver.profile_for(profile_l['counterpart']['index'],
                                             profile_l['counterpart']['level'], 'R',
                                             namespace=profile_l['counterpart']['namespace'])
            assert profile_l['profile_hash'] == profile_r['profile_hash']
            assert [item['index'] for item in profile_l['left_leaves']] == [4, 5, 8, 9, 10]
            assert [item['index'] for item in profile_l['right_leaves']] == [504, 505, 508, 509, 510]
            passed('real ARM CSV resolves ACC L3 to five explicit bilateral leaves with stable paired profile identity')

            baseline_groups = ns['run'](working_side='L')
            baseline_input = glob['_input_names'](glob['REF_PATH'], glob['ARM_PATH'])
            baseline_arm = glob['_find'](baseline_input['atlas_name'])
            baseline_group_ids = {side: baseline_groups[side].GetID() for side in ('L', 'R')}

            def editor_snapshot():
                nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLSegmentEditorNode')
                state = []
                for idx in range(nodes.GetNumberOfItems()):
                    node = nodes.GetItemAsObject(idx)
                    segmentation_node = node.GetSegmentationNode()
                    source_volume = node.GetSourceVolumeNode()
                    state.append((node.GetID(), segmentation_node.GetID() if segmentation_node else None,
                                  source_volume.GetID() if source_volume else None,
                                  node.GetMaskSegmentID(), node.GetMaskMode(), node.GetSelectedSegmentID(),
                                  node.GetActiveEffectName(), node.GetOverwriteMode()))
                return state

            def baseline_mask_hashes():
                hashes = {}
                for side in ('L', 'R'):
                    node = baseline_groups[side]
                    data = node.GetSegmentation()
                    for idx in range(data.GetNumberOfSegments()):
                        segment_id = data.GetNthSegmentID(idx)
                        mask = slicer.util.arrayFromSegmentBinaryLabelmap(node, segment_id, baseline_arm)
                        hashes[f'{side}:{segment_id}'] = hashlib.sha256(
                            np.ascontiguousarray(mask).tobytes()).hexdigest()
                return hashes

            baseline_editor_state = editor_snapshot()
            baseline_masks = baseline_mask_hashes()
            assert baseline_masks
            passed('preloaded insula groups and Segment Editor state captured before hierarchy selection')

            import qt
            dialog = ns['show_gui']()
            slicer.app.processEvents()
            scene_before_search = slicer.mrmlScene.GetNumberOfNodes()
            mode = dialog.findChild(qt.QComboBox, 'RegionGroupMode')
            hierarchy_edit = dialog.findChild(qt.QLineEdit, 'ARMHierarchyCSVPath')
            search_edit = dialog.findChild(qt.QLineEdit, 'ARMHierarchySearch')
            search_side = next(combo for combo in dialog.findChildren(qt.QComboBox)
                               if combo.objectName != 'RegionGroupMode'
                               and [combo.itemText(i) for i in range(combo.count)] == ['Both', 'L', 'R'])
            search_level = next(combo for combo in dialog.findChildren(qt.QComboBox)
                                if [combo.itemText(i) for i in range(combo.count)] ==
                                ['Any level', '1', '2', '3', '4', '5', '6'])
            results = dialog.findChild(qt.QComboBox, 'ARMHierarchyResults')
            search_button = next(button for button in dialog.findChildren(qt.QPushButton)
                                 if button.text == 'Search')
            use_button = next(button for button in dialog.findChildren(qt.QPushButton)
                              if button.text == 'Use selected region (pending)')
            hierarchy_edit.setText(str(hierarchy_path))
            mode.setCurrentIndex(1)
            search_edit.setText('CL_ACC')
            search_side.setCurrentIndex(1)
            search_level.setCurrentIndex(3)
            search_button.click()
            slicer.app.processEvents()
            assert results.count == 1 and 'CL_ACC' in results.itemText(0)
            assert slicer.mrmlScene.GetNumberOfNodes() == scene_before_search
            use_button.click()
            slicer.app.processEvents()
            assert slicer.mrmlScene.GetNumberOfNodes() == scene_before_search
            assert editor_snapshot() == baseline_editor_state
            assert baseline_mask_hashes() == baseline_masks
            assert {side: baseline_groups[side].GetID() for side in ('L', 'R')} == baseline_group_ids
            assert '5 L6 IDs' in dialog.findChild(qt.QLabel, 'ARMHierarchyProfilePreview').text
            passed('GUI hierarchy search and pending selection do not mutate MRML scene')

            load_button = next(button for button in dialog.findChildren(qt.QPushButton)
                               if button.text == 'Validate inputs and load groups')
            load_button.click()
            slicer.app.processEvents()
            loaded = {side: glob['_find'](glob['ACTIVE_SEG_NAMES'][side]) for side in ('L', 'R')}
            assert all(node is not None for node in loaded.values())
            input_info = glob['_input_names'](glob['REF_PATH'], glob['ARM_PATH'], profile_l)
            arm = glob['_find'](input_info['atlas_name'])
            template = glob['_find'](input_info['template_name'])
            assert set(loaded) == {'L', 'R'}
            editor = slicer.modules.segmenteditor.widgetRepresentation().self().editor
            parameters = editor.mrmlSegmentEditorNode()
            assert parameters.GetSegmentationNode().GetID() == loaded['L'].GetID()
            assert len(profile_l['left_leaves']) == len(profile_l['right_leaves']) == 5
            assert np.count_nonzero(np.isin(slicer.util.arrayFromVolume(arm), glob['FULL_INS_IDS']['L'])) > 0
            assert np.count_nonzero(np.isin(slicer.util.arrayFromVolume(arm), glob['FULL_INS_IDS']['R'])) > 0
            matrix = glob['_node_geometry_matrix'](template)
            def centroid_x(mask):
                kji = np.argwhere(mask).mean(axis=0)
                ijk = np.asarray([kji[2], kji[1], kji[0], 1.0])
                return float((matrix @ ijk)[0])
            assert centroid_x(np.isin(slicer.util.arrayFromVolume(arm), glob['FULL_INS_IDS']['L'])) < 0
            assert centroid_x(np.isin(slicer.util.arrayFromVolume(arm), glob['FULL_INS_IDS']['R'])) > 0
            passed('hierarchy GUI load creates both five-leaf groups, keeps scope geometry, and initially focuses the selected left group')

            # Selecting the paired profile from the right gives the same nodes and right-hand editor focus.
            loaded_r = ns['run'](region_profile=profile_r, working_side='R')
            assert loaded_r['L'].GetID() == loaded['L'].GetID()
            assert loaded_r['R'].GetID() == loaded['R'].GetID()
            assert parameters.GetSegmentationNode().GetID() == loaded['R'].GetID()
            passed('paired right-side selection reuses the same groups and focuses the right working group')
            working_side = dialog.findChild(qt.QComboBox, 'WorkingHemisphere')
            working_side.setCurrentIndex(1)
            slicer.app.processEvents()
            assert dialog.findChild(qt.QLabel, 'MirrorDirection').text == 'R → L'
            pre_mirror_editor_state = editor_snapshot()

            left = loaded['L']
            left_data = left.GetSegmentation()
            right_data = loaded['R'].GetSegmentation()
            right_before = {right_data.GetNthSegmentID(i):
                slicer.util.arrayFromSegmentBinaryLabelmap(loaded['R'], right_data.GetNthSegmentID(i), arm).astype(bool)
                for i in range(right_data.GetNumberOfSegments())}
            source_arrays = {left_data.GetNthSegmentID(i):
                slicer.util.arrayFromSegmentBinaryLabelmap(left, left_data.GetNthSegmentID(i), arm).astype(bool)
                for i in range(left_data.GetNumberOfSegments())}
            helper_id = 'L-local-parent'
            helper = np.logical_or(source_arrays['ARM_L6_4'], source_arrays['ARM_L6_5'])
            left_data.AddEmptySegment(helper_id, helper_id, (0.2, 0.8, 0.7))
            left_data.GetSegment(helper_id).SetTag('Insula.MirrorRole', 'helper_mask')
            left_data.GetSegment(helper_id).SetTag('ReviewEvidence', 'preserve hierarchy helper metadata')
            slicer.util.updateSegmentBinaryLabelmapFromArray(helper.astype(np.uint8), left, helper_id, arm)
            left.GetDisplayNode().SetSegmentVisibility(helper_id, False)
            source_before = {**source_arrays, helper_id: helper.copy()}
            scene_count = slicer.mrmlScene.GetNumberOfNodes()
            dry_run = ns['mirror_side']('L', source_node=left, dry_run=True)
            assert slicer.mrmlScene.GetNumberOfNodes() == scene_count
            candidate = ns['mirror_side']('L', source_node=left)
            candidate_arrays = {candidate.GetSegmentation().GetNthSegmentID(i):
                slicer.util.arrayFromSegmentBinaryLabelmap(candidate,
                    candidate.GetSegmentation().GetNthSegmentID(i), arm).astype(bool)
                for i in range(candidate.GetSegmentation().GetNumberOfSegments())}
            expected_pairs = {item['left_id']: item['right_id'] for item in profile_l['pair_map']}
            for left_id, right_id in expected_pairs.items():
                assert np.array_equal(candidate_arrays[f'ARM_L6_{right_id}'],
                                      source_before[f'ARM_L6_{left_id}'][..., ::-1])
            assert np.array_equal(candidate_arrays[glob['SCOPE_IDS']['R']],
                                  source_before[glob['SCOPE_IDS']['L']][..., ::-1])
            assert np.array_equal(candidate_arrays['R-local-parent'], helper[..., ::-1])
            assert not candidate.GetDisplayNode().GetSegmentVisibility(glob['SCOPE_IDS']['R'])
            assert not candidate.GetDisplayNode().GetSegmentVisibility('R-local-parent')
            assert candidate.GetSegmentation().GetSegment('R-local-parent').GetTag(
                'ReviewEvidence', vtk.mutable(''))
            assert all(np.array_equal(slicer.util.arrayFromSegmentBinaryLabelmap(left, sid, arm).astype(bool), mask)
                       for sid, mask in source_before.items())
            assert all(np.array_equal(slicer.util.arrayFromSegmentBinaryLabelmap(loaded['R'], sid, arm).astype(bool), mask)
                       for sid, mask in right_before.items())
            passed('mirror uses the CSV-derived bilateral ID map; tagged helper is excluded from partition, hidden, and preserved')

            restored = ns['mirror_side']('R', source_node=candidate)
            restored_arrays = {restored.GetSegmentation().GetNthSegmentID(i):
                slicer.util.arrayFromSegmentBinaryLabelmap(restored,
                    restored.GetSegmentation().GetNthSegmentID(i), arm).astype(bool)
                for i in range(restored.GetSegmentation().GetNumberOfSegments())}
            for left_id, right_id in expected_pairs.items():
                assert np.array_equal(restored_arrays[f'ARM_L6_{left_id}'],
                                      source_before[f'ARM_L6_{left_id}'])
            assert np.array_equal(restored_arrays[glob['SCOPE_IDS']['L']],
                                  source_before[glob['SCOPE_IDS']['L']])
            assert np.array_equal(restored_arrays['L-local-parent'], helper)
            passed('right-to-left hierarchy mirror round-trips every selected L6 leaf and helper mask')

            candidate_path = output / 'ARMins_hierarchy_ACC_candidate.seg.nrrd'
            receipt['saved_candidate'] = ns['save_mirrored_candidate'](candidate, candidate_path)
            reloaded = slicer.util.loadSegmentation(str(candidate_path))
            reloaded_scope = reloaded.GetSegmentation().GetSegment(glob['SCOPE_IDS']['R'])
            receipt_tag = vtk.mutable('')
            assert reloaded_scope.GetTag('Insula.MirrorReceipt', receipt_tag)
            saved_receipt = json.loads(str(receipt_tag))
            assert saved_receipt['region_profile']['profile_hash'] == profile_l['profile_hash']
            helper_tag = vtk.mutable('')
            assert reloaded.GetSegmentation().GetSegment('R-local-parent').GetTag(
                'ReviewEvidence', helper_tag)
            assert str(helper_tag) == 'preserve hierarchy helper metadata'
            reloaded_arrays = {reloaded.GetSegmentation().GetNthSegmentID(i):
                slicer.util.arrayFromSegmentBinaryLabelmap(reloaded,
                    reloaded.GetSegmentation().GetNthSegmentID(i), arm).astype(bool)
                for i in range(reloaded.GetSegmentation().GetNumberOfSegments())}
            assert set(reloaded_arrays) == set(candidate_arrays)
            assert all(np.array_equal(reloaded_arrays[sid], values)
                       for sid, values in candidate_arrays.items())
            passed('hierarchy candidate save/reload retains the profile receipt and helper annotation')

            mirror_button = next(button for button in dialog.findChildren(qt.QPushButton)
                                 if 'Mirror selected side' in button.text)
            count_before_gui_mirror = slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLSegmentationNode')
            mirror_button.click()
            slicer.app.processEvents()
            assert slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLSegmentationNode') == count_before_gui_mirror + 1
            assert any(button.enabled for button in dialog.findChildren(qt.QPushButton)
                       if 'Save mirrored candidate' in button.text)
            passed('native hierarchy mirror button creates a separate candidate and enables candidate saving')

            assert editor_snapshot() == pre_mirror_editor_state
            assert baseline_mask_hashes() == baseline_masks
            assert {side: baseline_groups[side].GetID() for side in ('L', 'R')} == baseline_group_ids
            passed('hierarchy mirroring leaves pre-existing insula working groups and Segment Editor references/mask/effect unchanged')

            after_input_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in input_file_paths}
            assert after_input_hashes == original_input_hashes
            receipt['immutable_input_hashes'] = after_input_hashes
            passed('registered template, atlas, and hierarchy CSV hashes are unchanged')

            dialog.close()
        elif phase == 'behavior':
            # Inputs are supplied through process-local environment variables.
            groups = ns['run']()
            input_info = glob['_input_names'](glob['REF_PATH'], glob['ARM_PATH'])
            arm = glob['_find'](input_info['atlas_name'])
            original_files = [Path(glob['REF_PATH']), Path(glob['ARM_PATH'])]
            hashes_before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in original_files}

            def arrays(node):
                data = node.GetSegmentation()
                return {data.GetNthSegmentID(i):
                    slicer.util.arrayFromSegmentBinaryLabelmap(node, data.GetNthSegmentID(i), arm).astype(bool)
                    for i in range(data.GetNumberOfSegments())}

            left, right = groups['L'], groups['R']
            right_before = arrays(right)
            # One deliberately asymmetric transfer plus one custom child, confined to a parent.
            original_left = arrays(left)
            donor = original_left['ARM_L6_42'].copy()
            target = original_left['ARM_L6_228'].copy()
            points = np.argwhere(donor)
            p0, p1 = tuple(points[0]), tuple(points[1])
            donor[p0] = False
            target[p0] = True
            donor[p1] = False
            child = np.zeros_like(donor)
            child[p1] = True
            child_id = ns['add_parcel']('mirror-test-child', 'L')
            for sid, value in [('ARM_L6_42', donor), ('ARM_L6_228', target), (child_id, child)]:
                slicer.util.updateSegmentBinaryLabelmapFromArray(value.astype(np.uint8), left, sid, arm)
            left.GetSegmentation().GetSegment('ARM_L6_228').SetTag(
                'ReviewEvidence', 'synthetic user annotation preserved')
            left_before = arrays(left)
            count_before = slicer.mrmlScene.GetNumberOfNodes()
            receipt['dry_run'] = ns['mirror_side']('L', dry_run=True)
            assert slicer.mrmlScene.GetNumberOfNodes() == count_before
            assert all(np.array_equal(a, arrays(left)[sid]) for sid, a in left_before.items())
            passed('dry run validates actual edited data without changing scene or source masks')

            candidate = ns['mirror_side']('L')
            receipt['candidate_name'] = candidate.GetName()
            assert candidate.GetName() == receipt['dry_run']['candidate_name']
            mirrored = arrays(candidate)
            receipt['mirrored_counts'] = {sid: int(a.sum()) for sid, a in mirrored.items()}
            receipt['mirror_mismatches'] = {}
            for sid, value in left_before.items():
                if sid == glob['SCOPE_IDS']['L']:
                    dest = glob['SCOPE_IDS']['R']
                elif sid.startswith('ARM_L6_'):
                    dest = 'ARM_L6_' + str(int(sid.split('_')[-1]) + 500)
                else:
                    dest = 'R-' + sid[2:]
                receipt['mirror_mismatches'][dest] = int(np.count_nonzero(mirrored[dest] != value[..., ::-1]))
                assert np.array_equal(mirrored[dest], value[..., ::-1]), (sid, dest)
            passed('all ARM IDs and custom child mirror exactly across KJI axis 2')
            assert all(np.array_equal(arrays(left)[sid], a) for sid, a in left_before.items())
            assert all(np.array_equal(arrays(right)[sid], a) for sid, a in right_before.items())
            passed('both existing working side nodes remain byte-for-byte equal as arrays')
            restored = ns['mirror_side']('R', source_node=candidate)
            restored_arrays = arrays(restored)
            assert all(np.array_equal(restored_arrays[sid], a) for sid, a in left_before.items())
            passed('right-to-left reflection restores every edited source voxel and parcel ID')

            result_path = output / 'ARMins_mirrored_candidate_test.seg.nrrd'
            receipt['saved_candidate'] = ns['save_mirrored_candidate'](candidate, result_path)
            reloaded = slicer.util.loadSegmentation(str(result_path))
            loaded_arrays = arrays(reloaded)
            assert set(loaded_arrays) == set(mirrored)
            assert all(np.array_equal(loaded_arrays[sid], a) for sid, a in mirrored.items())
            passed('saved native .seg.nrrd reloads with every segment and voxel unchanged')
            import vtk
            saved_provenance = vtk.mutable('')
            assert reloaded.GetSegmentation().GetSegment(glob['SCOPE_IDS']['R']).GetTag(
                'Insula.MirrorReceipt', saved_provenance)
            receipt['reloaded_provenance'] = json.loads(str(saved_provenance))
            assert receipt['reloaded_provenance']['loader_version'] == ns['VERSION']
            assert receipt['reloaded_provenance']['processing_timezone'] == 'UTC'
            assert receipt['reloaded_provenance']['generated_at'].endswith('+00:00')
            passed('mirror provenance survives .seg.nrrd reload as a scope-segment tag')
            annotation = vtk.mutable('')
            assert reloaded.GetSegmentation().GetSegment('ARM_L6_728').GetTag('ReviewEvidence', annotation)
            assert str(annotation) == 'synthetic user annotation preserved'
            passed('arbitrary source annotation metadata survives mirroring and native save/reload')
            try:
                ns['save_mirrored_candidate'](candidate, result_path)
                raise AssertionError('existing output was overwritten')
            except FileExistsError:
                passed('existing mirror output is refused without overwrite')

            # Exercise the real Qt signal connections after the design image was reviewed.
            import qt
            dialog = ns['show_gui']()
            buttons = dialog.findChildren(qt.QPushButton)
            load_button = next(b for b in buttons if b.text == 'Validate inputs and load groups')
            mirror_button = next(b for b in buttons if 'Mirror selected side' in b.text)
            load_button.click()
            slicer.app.processEvents()
            assert mirror_button.enabled
            node_count = slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLSegmentationNode')
            mirror_button.click()
            slicer.app.processEvents()
            assert slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLSegmentationNode') == node_count + 1
            assert any(b.enabled for b in buttons if 'Save mirrored candidate' in b.text)
            image_path = output / 'mirror_dialog_after.png'
            assert dialog.grab().save(str(image_path))
            receipt['screenshot'] = str(image_path)
            passed('native Validate and Mirror button signals create a new candidate and enable saving')
            dialog.close()

            # Reproduce the historical failure mechanism in memory only.
            bad_target = target.copy()
            overlap_point = tuple(np.argwhere(original_left['ARM_L6_43'])[0])
            bad_target[overlap_point] = True
            slicer.util.updateSegmentBinaryLabelmapFromArray(bad_target.astype(np.uint8), left, 'ARM_L6_228', arm)
            node_count = slicer.mrmlScene.GetNumberOfNodes()
            try:
                ns['mirror_side']('L')
                raise AssertionError('overlapping source was mirrored')
            except ValueError as error:
                assert 'overlap' in str(error).lower(), str(error)
                assert slicer.mrmlScene.GetNumberOfNodes() == node_count
                receipt['overlap_rejection'] = str(error)
                passed('overlap with another seed is rejected before creating any candidate')
            hashes_after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in original_files}
            assert hashes_before == hashes_after
            receipt['immutable_input_hashes'] = hashes_after
            passed('registered source image and atlas hashes remain unchanged')
        else:
            raise ValueError('phase must be design, behavior, or hierarchy')
        receipt['status'] = 'passed'
    except Exception:
        receipt['status'] = 'failed'
        receipt['error'] = traceback.format_exc()
        raise
    finally:
        receipt_path.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')


try:
    main()
except Exception:
    traceback.print_exc()
    slicer.app.exit(1)
else:
    slicer.app.exit(0)
