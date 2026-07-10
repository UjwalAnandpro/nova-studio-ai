import unittest
import os
import sys
import shutil
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.models.timeline import Timeline, TimelineTrack, TimelineClip
from core.projects.manager import project_manager
from core.timeline.manager import timeline_manager
from core.timeline.version_manager import version_manager
from core.timeline.thumbnail import thumbnail_generator
from core.renderer.builder import ffmpeg_builder
from core.renderer.worker import render_queue

class TestTimelineRenderEngine(unittest.TestCase):

    def setUp(self):
        # Create a mock project for testing
        self.proj_name = "Timeline Test Proj"
        self.meta = project_manager.create_project(self.proj_name, "Testing timeline & editor operations")
        self.proj_dir = project_manager.get_project_dir(self.meta.id)
        
        # Build standard timeline tracks
        self.timeline = Timeline(
            tracks=[
                TimelineTrack(id="track_3_images", name="Images Track", type="video"),
                TimelineTrack(id="track_1_voice", name="Voice Track", type="audio")
            ]
        )
        
        # Add mock image clip
        self.img_clip = TimelineClip(
            id="clip_img_1",
            type="image",
            path="images/scene_1.png",
            start_time=0.0,
            duration=5.0
        )
        timeline_manager.add_clip(self.timeline, "track_3_images", self.img_clip)

    def tearDown(self):
        # Clean up
        project_manager.delete_project(self.meta.id)

    def test_timeline_split_clip(self):
        """Tests splitting a clip updates trims and duration correctly."""
        # Split clip at 2.0s
        success = timeline_manager.split_clip(self.timeline, "clip_img_1", 2.0)
        self.assertTrue(success)
        
        # Should now have 2 clips on track
        track = timeline_manager.get_track(self.timeline, "track_3_images")
        self.assertEqual(len(track.clips), 2)
        
        # Check first clip
        c1 = track.clips[0]
        self.assertEqual(c1.duration, 2.0)
        self.assertEqual(c1.trim_end, 3.0)
        
        # Check second clip
        c2 = track.clips[1]
        self.assertEqual(c2.start_time, 2.0)
        self.assertEqual(c2.duration, 3.0)
        self.assertEqual(c2.trim_start, 2.0)

    def test_timeline_ripple_delete(self):
        """Tests deleting a clip shifts subsequent clips backward."""
        # Add another clip starting at 10.0s, duration 4.0s
        clip2 = TimelineClip(
            id="clip_img_2",
            type="image",
            path="images/scene_2.png",
            start_time=10.0,
            duration=4.0
        )
        timeline_manager.add_clip(self.timeline, "track_3_images", clip2)
        
        # Ripple delete first clip (duration 5.0)
        success = timeline_manager.ripple_delete(self.timeline, "clip_img_1")
        self.assertTrue(success)
        
        # Should have 1 clip left
        track = timeline_manager.get_track(self.timeline, "track_3_images")
        self.assertEqual(len(track.clips), 1)
        
        # The remaining clip should be shifted from 10.0s to 5.0s
        c = track.clips[0]
        self.assertEqual(c.id, "clip_img_2")
        self.assertEqual(c.start_time, 5.0)

    def test_version_snapshots(self):
        """Tests saving and loading revisions of timeline.json."""
        # Save version
        success = version_manager.save_version(self.meta.id, self.timeline, "Snapshot 1")
        self.assertTrue(success)
        
        # List history snapshot list
        history = version_manager.list_versions(self.meta.id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["comment"], "Snapshot 1")
        
        # Restore version
        restored = version_manager.restore_version(self.meta.id, history[0]["filename"])
        self.assertIsNotNone(restored)
        track = timeline_manager.get_track(restored, "track_3_images")
        self.assertEqual(len(track.clips), 1)

    def test_ffmpeg_command_builder(self):
        """Tests compiling FFmpeg commands dynamically."""
        # Create output path
        out_path = os.path.join(self.proj_dir, "export.mp4")
        
        # Build
        args, filter_str = ffmpeg_builder.build_render_command(self.timeline, self.meta.id, out_path)
        self.assertGreater(len(args), 0)
        self.assertIn("-filter_complex", args)
        self.assertIn("v_scaled_0", filter_str)

    def test_render_queue_background_thread(self):
        """Tests adding render job and cancelling it."""
        out_path = os.path.join(self.proj_dir, "export.mp4")
        
        # Simple fast mock command list (checks -version)
        cmd_args = ["-version"]
        
        job_id = render_queue.add_job(self.meta.id, out_path, cmd_args, total_duration=5.0)
        self.assertIsNotNone(job_id)
        
        job = render_queue.get_job(job_id)
        self.assertIsNotNone(job)
        self.assertIn(job.status, ("Queued", "Running"))
        
        # Cancel the job
        render_queue.cancel_job(job_id)
        self.assertEqual(job.status, "Cancelled")

if __name__ == "__main__":
    unittest.main()
