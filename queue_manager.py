# --- START OF FILE queue_manager.py ---
# START OF FILE queue_manager.py

import json
import os
import re
from datetime import datetime
import traceback

class QueueManager:
    def __init__(self, log_directory="logs"):
        self.log_directory = log_directory
        self.ensure_log_directory()
        self.pending_jobs = {}
        self.completed_jobs = {}
        self.cancelled_jobs = {}
        self.job_first_file_seen = {}
        self.startup_completed = False
        self.load_logs_on_startup()

    def ensure_log_directory(self):
        if not os.path.exists(self.log_directory):
            try:
                os.makedirs(self.log_directory)
                print(f"Created log directory: {self.log_directory}")
            except OSError as e:
                print(f"CRITICAL ERROR: Could not create log directory '{self.log_directory}': {e}")

    def _get_log_paths(self, date_str=None):
        if date_str is None: date_str = datetime.now().strftime("%Y-%m-%d")
        pending_log = os.path.join(self.log_directory, f"{date_str}-pending.json")
        completed_log = os.path.join(self.log_directory, f"{date_str}-completed.json")
        cancelled_log = os.path.join(self.log_directory, f"{date_str}-cancelled.json")
        return pending_log, completed_log, cancelled_log

    def load_logs_on_startup(self):
        print("QueueManager: Loading previous logs...")

        available_dates = []
        try:
            for entry in os.listdir(self.log_directory):
                match = re.match(r"(\d{4}-\d{2}-\d{2})-(pending|completed|cancelled)\.json$", entry)
                if match:
                    available_dates.append(match.group(1))
        except OSError as e:
            print(f"Warning: Could not inspect log directory '{self.log_directory}': {e}")

        unique_dates = sorted(set(available_dates))
        if not unique_dates:
            unique_dates = [datetime.now().strftime("%Y-%m-%d")]

        recent_dates = unique_dates[-7:]

        for date_str in recent_dates:
            pending_path, completed_path, cancelled_path = self._get_log_paths(date_str)
            self._load_log_file(pending_path, self.pending_jobs)
            self._load_log_file(completed_path, self.completed_jobs)
            self._load_log_file(cancelled_path, self.cancelled_jobs)

        print(
            "Loaded pending/completed/cancelled jobs from dates: "
            + ", ".join(recent_dates)
        )
        print(f"Current queue contains {len(self.pending_jobs)} pending jobs after startup load.")
        self.job_first_file_seen = {}
        self.startup_completed = True

    def _load_log_file(self, file_path, target_dict):
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f: content = f.read()
                if not content.strip():
                    return
                data = json.loads(content)
                if isinstance(data, dict): valid_data = {k: v for k, v in data.items() if isinstance(v, dict)}; target_dict.update(valid_data)
                else: print(f"Warning: Log file {file_path} invalid format.")
            except json.JSONDecodeError as e: print(f"Error decoding {file_path}: {e}"); print(f"Near: {content[max(0, e.pos-20):e.pos+20]}")
            except (OSError, TypeError) as e: print(f"Error loading {file_path}: {e}")
            except Exception as e: print(f"Unexpected error loading {file_path}: {e}"); traceback.print_exc()

    def _write_log_file(self, file_path, data_dict):
        try:
            temp_file_path = file_path + ".tmp"
            with open(temp_file_path, 'w') as f: json.dump(data_dict, f, indent=2)
            os.replace(temp_file_path, file_path)
        except (OSError, TypeError) as e: print(f"Error writing log file {file_path}: {e}")
        except Exception as e: print(f"Unexpected error writing log file {file_path}: {e}")

    def _update_daily_logs(self):
        pending_path, completed_path, cancelled_path = self._get_log_paths()
        self._write_log_file(pending_path, self.pending_jobs)
        self._write_log_file(completed_path, self.completed_jobs)
        self._write_log_file(cancelled_path, self.cancelled_jobs)

    def add_job(self, job_id, job_data):
        job_id_str = str(job_id)
        if job_id_str in self.pending_jobs or job_id_str in self.completed_jobs or job_id_str in self.cancelled_jobs:
             print(f"Warning: Job ID {job_id_str} already exists. Overwriting.")
             self.completed_jobs.pop(job_id_str, None)
             self.cancelled_jobs.pop(job_id_str, None)

        timestamp = datetime.now().isoformat()
        full_job_data = {
            "timestamp": timestamp, "status": "pending", "job_id": job_id_str,
            "comfy_prompt_id": job_data.get("comfy_prompt_id"), "message_id": job_data.get("message_id"),
            "channel_id": job_data.get("channel_id"), "user_id": job_data.get("user_id"),
            "user_name": job_data.get("user_name"), "user_mention": job_data.get("user_mention"),
            "prompt": job_data.get("prompt", "[No Prompt Text]"), "batch_size": job_data.get("batch_size", 1),
            "seed": job_data.get("seed"), "steps": job_data.get("steps"),
            "guidance": job_data.get("guidance"), # Flux guidance
            "guidance_sdxl": job_data.get("guidance_sdxl"), # SDXL guidance
            "guidance_qwen": job_data.get("guidance_qwen"),
            "guidance_wan": job_data.get("guidance_wan"),
            "negative_prompt": job_data.get("negative_prompt"), # SDXL negative prompt
            "style": job_data.get("style"), "width": job_data.get("width"), "height": job_data.get("height"),
            "aspect_ratio_str": job_data.get("aspect_ratio_str"),
            "model_used": job_data.get("model_used"), "parameters_used": job_data.get("parameters_used",{}),
            "original_ar_param": job_data.get("original_ar_param"), "image_url": job_data.get("image_url"),
            "img_strength_percent": job_data.get("img_strength_percent"), "denoise": job_data.get("denoise"),
            "type": job_data.get("type", "generate"), "original_prompt_id": job_data.get("original_prompt_id"),
            "image_index": job_data.get("image_index"), "variation_type": job_data.get("variation_type"),
            "upscale_factor": job_data.get("upscale_factor"),
            "enhancer_used": job_data.get("enhancer_used", False),
            "original_prompt": job_data.get("original_prompt"),
            "enhanced_prompt": job_data.get("enhanced_prompt"),
            "enhancer_error": job_data.get("enhancer_error"),
            "llm_provider": job_data.get("llm_provider"),
            "model_type_for_enhancer": job_data.get("model_type_for_enhancer", "flux"),
            "mp_size": job_data.get("mp_size"),
            "supports_animation": job_data.get("supports_animation"),
            "followup_animation_workflow": job_data.get("followup_animation_workflow"),
            "wan_animation_resolution": job_data.get("wan_animation_resolution"),
            "wan_animation_duration": job_data.get("wan_animation_duration"),
            "wan_animation_motion_profile": job_data.get("wan_animation_motion_profile"),
            "animation_prompt_text": job_data.get("animation_prompt_text"),
        }
        self.pending_jobs[job_id_str] = full_job_data
        print(f"Added job {job_id_str} to pending queue.")
        self._update_daily_logs()

    def get_pending_job_by_id(self, job_id): return self.pending_jobs.get(str(job_id))
    def get_pending_jobs(self): return self.pending_jobs.copy()

    def mark_job_complete(self, job_id, job_data, image_paths: list):
        job_id_str = str(job_id)
        if job_id_str in self.pending_jobs:
            completed_job_data = job_data
            self.pending_jobs.pop(job_id_str, None) # Remove from pending
            
            completed_job_data["status"] = "complete"
            completed_job_data["completion_time"] = datetime.now().isoformat()
            completed_job_data["image_paths"] = [os.path.normpath(p) for p in image_paths]
            
            self.completed_jobs[job_id_str] = completed_job_data
            self.job_first_file_seen.pop(job_id_str, None)
            print(f"Moved job {job_id_str} to completed log.")
            self._update_daily_logs()
        elif job_id_str in self.cancelled_jobs: print(f"Info: Job {job_id_str} already cancelled, not marking complete.")
        elif job_id_str in self.completed_jobs: print(f"Info: Job {job_id_str} already complete.")
        else: print(f"Warning: Job {job_id_str} not found in pending to mark complete.")


    def mark_job_cancelled(self, job_id):
        job_id_str = str(job_id); cancelled_job_data = None
        if job_id_str in self.pending_jobs: cancelled_job_data = self.pending_jobs.pop(job_id_str); print(f"Moved job {job_id_str} from pending to cancelled.")
        elif job_id_str in self.completed_jobs: cancelled_job_data = self.completed_jobs.pop(job_id_str); print(f"Job {job_id_str} was complete, moving to cancelled.")
        elif job_id_str in self.cancelled_jobs: print(f"Job {job_id_str} already cancelled."); return
        if cancelled_job_data is None: print(f"Job {job_id_str} not found, creating basic cancelled entry."); cancelled_job_data = {"job_id": job_id_str, "status": "unknown_pre_cancel"}
        cancelled_job_data["status"] = "cancelled"; cancelled_job_data["cancellation_time"] = datetime.now().isoformat()
        self.cancelled_jobs[job_id_str] = cancelled_job_data
        self.job_first_file_seen.pop(job_id_str, None)
        self._update_daily_logs()

    def get_job_data(self, message_id, channel_id):
        message_id_str = str(message_id); channel_id_str = str(channel_id)
        for data in self.pending_jobs.values():
            if str(data.get('message_id')) == message_id_str and str(data.get('channel_id')) == channel_id_str: return data
        for data in self.completed_jobs.values():
            if str(data.get('message_id')) == message_id_str and str(data.get('channel_id')) == channel_id_str: return data
        for data in self.cancelled_jobs.values():
            if str(data.get('message_id')) == message_id_str and str(data.get('channel_id')) == channel_id_str: return data
        return None

    def get_job_data_by_id(self, job_id):
        job_id_str = str(job_id)
        if job_id_str in self.pending_jobs: return self.pending_jobs[job_id_str]
        if job_id_str in self.completed_jobs: return self.completed_jobs[job_id_str]
        if job_id_str in self.cancelled_jobs: return self.cancelled_jobs[job_id_str]
        return None

    def get_job_by_comfy_id(self, comfy_prompt_id):
         comfy_prompt_id_str = str(comfy_prompt_id)
         for data in self.pending_jobs.values():
             if 'comfy_prompt_id' in data and str(data.get('comfy_prompt_id')) == comfy_prompt_id_str: return data
         for data in self.completed_jobs.values():
              if 'comfy_prompt_id' in data and str(data.get('comfy_prompt_id')) == comfy_prompt_id_str: return data
         for data in self.cancelled_jobs.values():
              if 'comfy_prompt_id' in data and str(data.get('comfy_prompt_id')) == comfy_prompt_id_str: return data
         return None

    def get_job_id_by_comfy_id(self, comfy_prompt_id):
         comfy_prompt_id_str = str(comfy_prompt_id)
         for job_id, data in self.pending_jobs.items():
             if 'comfy_prompt_id' in data and str(data.get('comfy_prompt_id')) == comfy_prompt_id_str: return job_id
         for job_id, data in self.completed_jobs.items():
             if 'comfy_prompt_id' in data and str(data.get('comfy_prompt_id')) == comfy_prompt_id_str: return job_id
         for job_id, data in self.cancelled_jobs.items():
             if 'comfy_prompt_id' in data and str(data.get('comfy_prompt_id')) == comfy_prompt_id_str: return job_id
         return None

    def is_job_completed_or_cancelled(self, job_id):
        job_id_str = str(job_id); return job_id_str in self.completed_jobs or job_id_str in self.cancelled_jobs

    def record_first_file_seen(self, job_id):
        job_id_str = str(job_id)
        if job_id_str not in self.job_first_file_seen:
            self.job_first_file_seen[job_id_str] = datetime.now()

    def get_time_since_first_file(self, job_id):
        job_id_str = str(job_id)
        if job_id_str in self.job_first_file_seen: return datetime.now() - self.job_first_file_seen[job_id_str]
        return None

    def update_job_message_id(self, job_id, new_message_id):
        job_id_str = str(job_id)
        new_message_id_str = str(new_message_id)
        updated = False
        log_to_update = None

        if job_id_str in self.pending_jobs:
            self.pending_jobs[job_id_str]['message_id'] = new_message_id_str
            log_to_update = self.pending_jobs
            updated = True
        elif job_id_str in self.completed_jobs:
            self.completed_jobs[job_id_str]['message_id'] = new_message_id_str
            log_to_update = self.completed_jobs
            updated = True
        elif job_id_str in self.cancelled_jobs:
             self.cancelled_jobs[job_id_str]['message_id'] = new_message_id_str
             log_to_update = self.cancelled_jobs
             updated = True

        if updated:
            print(f"Updated message_id for job {job_id_str} to {new_message_id_str}")
            pending_path, completed_path, cancelled_path = self._get_log_paths()
            if log_to_update is self.pending_jobs:
                 self._write_log_file(pending_path, log_to_update)
            elif log_to_update is self.completed_jobs:
                 self._write_log_file(completed_path, log_to_update)
            elif log_to_update is self.cancelled_jobs:
                 self._write_log_file(cancelled_path, log_to_update)
        else:
            print(f"Warning: Could not update message_id for job {job_id_str} (not found in queues).")


queue_manager = QueueManager()
