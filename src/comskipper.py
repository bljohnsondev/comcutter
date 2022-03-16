import time
import shutil
import subprocess
import os
from threading import Thread
from queue import Queue

DEFAULT_TIMEOUT = 5400

processing = set()
queue = Queue()

class CommercialWorker(Thread):
    def __init__(self, logging, config):
        Thread.__init__(self)
        self.logging = logging
        self.config = config

    def run(self):
        while True:
            filepath = queue.get()
            try:
                self.logging.info("processing file: " + filepath)
                self.run_command(filepath)
            finally:
                queue.task_done()
                processing.remove(filepath)

    def build_command(self, filepath):
        comskip_cmd = self.config.get("comskip", "comskip_cmd")
        inifile = self.config.get("comskip", "comskip_ini")
        run_cmd = self.config.get("comskip", "cmd")
        keep_edl = self.config.get("comskip", "keep_edl")

        cmd = [
            run_cmd,
            '--comskip=' + comskip_cmd,
        ]

        if inifile is not None and inifile != "":
            cmd.append('--comskip-ini=' + inifile)

        if keep_edl == True:
            cmd.append('--keep-edl')
        
        cmd.append(filepath)
        
        return cmd

    def get_path_info(self, filepath):
        filename = os.path.basename(filepath)
        path = os.path.dirname(filepath)
        return (
            filename,
            path,
            os.path.join(path, filename + ".bak")
        )

    def backup_file(self, filepath):
        filename, path, backuppath = self.get_path_info(filepath)
        self.logging.debug("backing up file:\nsource      : %s\ndestination : %s" % (filepath, backuppath))
        shutil.copy(filepath, backuppath)
        self.logging.debug("backup complete")
    
    def remove_backup(self, filepath):
        filename, path, backuppath = self.get_path_info(filepath)
        os.remove(backuppath)

    def restore_backup(self, filepath):
        filename, path, backuppath = self.get_path_info(filepath)
        self.logging.debug("restoring backup file:\nsource      : %s\ndestination : %s" % (backuppath, filepath))
        shutil.move(backuppath, filepath)
        self.logging.debug("restore complete")

    def get_size_percent(self):
        size_percent = 0.9
        size_config = self.config.get("comskip", "size_percentage")
        if size_config is not None:
            size_percent = size_config
        return size_percent
        

    def check_size(self, filepath, original_size):
        size_percent = self.get_size_percent()
        if os.path.isfile(filepath):
            new_size = os.path.getsize(filepath)
            return (new_size > (original_size * size_percent)), new_size
        else:
            return False, 0

    def run_postprocess(self, filepath):
        postprocess_cmd = self.config.get("postprocess", "cmd")

        if postprocess_cmd is None or postprocess_cmd == "":
            return

        if not os.path.isfile(postprocess_cmd):
            self.logging.warning("could not run postprocess command: " + postprocess_cmd)
            return

        cmd = [
            postprocess_cmd,
            filepath
        ]

        self.logging.debug("running postprocess cmd: %s", " ".join(cmd))
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL)

        if result.returncode != 0:
            if result.stderr:
                self.logging.error("stderr [%d] when processing file: %s", result.returncode, result.stderr)
            else:
                self.logging.error("stderr [%d] when processing file: unknown error", result.returncode)

    def run_command(self, filepath):
        cmd = self.build_command(filepath)
        result = None

        if os.path.isfile(filepath):
            self.backup_file(filepath)
            filename = os.path.basename(filepath)
            original_size = 0.0

            timeout_config = self.config.get("comskip", "timeout")
            timeout_seconds = DEFAULT_TIMEOUT

            if timeout_config is not None and timeout_config > 0:
                timeout_seconds = int(timeout_config)

            try:
                original_size = os.path.getsize(filepath)
                self.logging.debug("running cmd [timeout %d]: %s" % (timeout_seconds, " ".join(cmd)))
                result = subprocess.run(cmd, stdout=subprocess.DEVNULL, timeout=timeout_seconds)
                self.logging.info("done processing file: " + filename)
                # check if something went wrong
                if not os.path.isfile(filepath):
                    raise Exception("file missing after commercial skip operation")
            except subprocess.TimeoutExpired as err:
                self.logging.error("timed out processing file: " + filename)
                self.restore_backup(filepath)
                return
            except Exception as err:
                self.logging.error("error processing file: " + filename)
                self.restore_backup(filepath)
                return

            if result.returncode == 0:
                new_size = os.path.getsize(filepath)
                self.logging.info("successfully processed: " + filename)
                # check the new file size to see if it's close in size to the original
                is_valid_size, new_size = self.check_size(filepath, original_size)
                if is_valid_size:
                    # size is OK so remove the backup
                    self.remove_backup(filepath)
                    self.run_postprocess(filepath)
                else:
                    size_percent = self.get_size_percent()
                    self.logging.error(
                        "new file size incorrect: old=%d - new=%d (%d%%, expected %d%%)",
                        original_size,
                        new_size,
                        ((new_size / original_size) * 100),
                        size_percent * 100
                    )
                    self.restore_backup(filepath)
            else:
                if result.stderr:
                    self.logging.error("stderr when processing file: " + result.stderr)
                else:
                    self.logging.error("an unknown error occurred")
                self.restore_backup(filepath)
        else:
            self.logger.error("file does not exist: " + filepath)

class CommercialSkipper:
    def __init__(self, logging, config):
        self.logging = logging
        self.config = config

        # initialize the worker queues
        for xwork in range(5):
            worker = CommercialWorker(logging, config)
            worker.daemon = True
            worker.start()

    def skip(self, ip, media_filepath):
        # strip the first / from the media filepath
        if media_filepath.startswith("/"):
            media_filepath = media_filepath[1:]

        library_dir = self.config.get("api", "library_dir") or "/library"
        filepath = os.path.join(library_dir, media_filepath)

        if os.path.exists(filepath):
            if filepath not in processing:
                processing.add(filepath)
                queue.put(filepath)
                return True, "processing"
            else:
                return False, "already processing"
        else:
            errmsg = "could not open file: " + filepath
            self.logging.warning("[%s] %s", ip, errmsg)
            return False, errmsg
