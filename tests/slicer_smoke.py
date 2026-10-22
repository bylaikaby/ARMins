"""Isolated native Slicer integration check for ARMins.

Version: 0.6.0 (local/unreleased)
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
and ARMINS_ATLAS (registered local 3-D L6 input). Optional: ARMINS_TEST_PHASE
('design' or 'behavior'; default behavior), ARMINS_OUTPUT_DIR.
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
            dialog = ns['show_gui']()
            slicer.app.processEvents()
            image_path = output / 'mirror_dialog.png'
            assert dialog.grab().save(str(image_path))
            receipt['screenshot'] = str(image_path)
            import qt
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
            help_dialog.close()
            slicer.app.processEvents()
            receipt['buttons'] = labels
            passed('actual native dialog contains both mirror controls; screenshot saved')
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
            raise ValueError('phase must be design or behavior')
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
