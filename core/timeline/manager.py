import copy
import uuid
from typing import Dict, Any, List, Optional, Tuple
from core.models.timeline import Timeline, TimelineTrack, TimelineClip
from core.projects.manager import project_manager
from core.logger.custom_logger import log_action

class TimelineManager:
    """
    Manages non-linear editing actions on the Timeline tracks and clips.
    Provides functions for splitting, ripple deletion, moving, and duplicating clips.
    """

    def get_track(self, timeline: Timeline, track_id: str) -> Optional[TimelineTrack]:
        """Gets a track from the timeline by ID."""
        for track in timeline.tracks:
            if track.id == track_id:
                return track
        return None

    def get_clip(self, timeline: Timeline, clip_id: str) -> Optional[Tuple[TimelineTrack, TimelineClip]]:
        """Finds a clip and its track by clip ID."""
        for track in timeline.tracks:
            for clip in track.clips:
                if clip.id == clip_id:
                    return track, clip
        return None

    def add_clip(self, timeline: Timeline, track_id: str, clip: TimelineClip) -> bool:
        """Appends a clip to a track."""
        track = self.get_track(timeline, track_id)
        if not track:
            return False
        track.clips.append(clip)
        return True

    def delete_clip(self, timeline: Timeline, clip_id: str) -> bool:
        """Removes a clip from its track."""
        found = self.get_clip(timeline, clip_id)
        if not found:
            return False
        track, clip = found
        track.clips.remove(clip)
        return True

    def move_clip(self, timeline: Timeline, clip_id: str, new_start_time: float) -> bool:
        """Moves a clip to a new start time on its track."""
        found = self.get_clip(timeline, clip_id)
        if not found:
            return False
        _, clip = found
        if clip.locked:
            return False
            
        clip.start_time = max(0.0, round(new_start_time, 2))
        return True

    def split_clip(self, timeline: Timeline, clip_id: str, split_time: float) -> bool:
        """
        Splits a clip into two separate clips at the specified split time.
        Adjusts start times, durations, and trim parameters so playback remains seamless.
        """
        found = self.get_clip(timeline, clip_id)
        if not found:
            return False
        track, clip = found
        if clip.locked:
            return False
            
        # Validate split time is within clip boundaries
        clip_end = clip.start_time + clip.duration
        if not (clip.start_time < split_time < clip_end):
            return False
            
        # Calculate split durations
        first_duration = round(split_time - clip.start_time, 2)
        second_duration = round(clip.duration - first_duration, 2)
        
        # Clone clip for the second segment
        second_clip = copy.deepcopy(clip)
        second_clip.id = f"{clip.id}_split_{str(uuid.uuid4())[:4]}"
        second_clip.start_time = round(split_time, 2)
        second_clip.duration = second_duration
        
        # Adjust trim values so the media lines up
        # Second clip offset advances by the first segment's length
        second_clip.trim_start = round(clip.trim_start + first_duration * clip.playback_speed, 2)
        
        # Shorten the first clip
        clip.duration = first_duration
        clip.trim_end = round(clip.trim_end + second_duration * clip.playback_speed, 2)
        
        # Add the second clip to the track right after the first
        idx = track.clips.index(clip)
        track.clips.insert(idx + 1, second_clip)
        
        log_action("TimelineManager", "SplitClip", "SUCCESS", 0.0, f"Split clip {clip_id} at {split_time}s")
        return True

    def ripple_delete(self, timeline: Timeline, clip_id: str) -> bool:
        """
        Deletes a clip and pulls all subsequent clips back by the deleted clip's duration
        to close the gap on the timeline.
        """
        found = self.get_clip(timeline, clip_id)
        if not found:
            return False
        track, clip = found
        if clip.locked:
            return False
            
        deleted_duration = clip.duration
        deleted_start = clip.start_time
        
        # Remove clip
        track.clips.remove(clip)
        
        # Shift subsequent clips
        shifted_count = 0
        for c in track.clips:
            if c.start_time > deleted_start:
                c.start_time = max(0.0, round(c.start_time - deleted_duration, 2))
                shifted_count += 1
                
        log_action("TimelineManager", "RippleDelete", "SUCCESS", 0.0, f"Ripple deleted {clip_id}, shifted {shifted_count} clips")
        return True

    def duplicate_clip(self, timeline: Timeline, clip_id: str) -> Optional[TimelineClip]:
        """Creates a duplicate copy of a clip right after it."""
        found = self.get_clip(timeline, clip_id)
        if not found:
            return None
        track, clip = found
        
        dup = copy.deepcopy(clip)
        dup.id = f"{clip.id}_copy_{str(uuid.uuid4())[:4]}"
        dup.start_time = round(clip.start_time + clip.duration, 2)
        
        # Check overlaps or simply append
        track.clips.append(dup)
        log_action("TimelineManager", "DuplicateClip", "SUCCESS", 0.0, f"Duplicated clip {clip_id}")
        return dup

# Singleton TimelineManager
timeline_manager = TimelineManager()
