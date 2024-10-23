import sys

def print_progress_bar(job_title, progress, length):
    if length != 0:        
        progress = int((progress * 100) / length)
    else:
        progress = 100
    sys.stdout.write("\r  " + job_title + " %d%%" % progress)
    sys.stdout.flush()
