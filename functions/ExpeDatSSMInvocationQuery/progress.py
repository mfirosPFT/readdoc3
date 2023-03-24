from datetime import datetime, timedelta


def extract_info_progress(input_str):
    lines = input_str.strip().split('\n')
    total_size = int(lines[-1].split('\t')[-1])
    downloaded_size = int(lines[-1].split('\t')[-2])
    duration = int(lines[-1].split('\t')[4])

    def convert_duration(duration):
        seconds = duration // 1000
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds %= 60
            return f"{minutes}m {seconds}s"
        else:
            hours = seconds // 3600
            seconds %= 3600
            minutes = seconds // 60
            seconds %= 60
            return f"{hours}h {minutes}m {seconds}s"

    def convert_size(size):
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
        suffix_index = 0
        while size >= 1024 and suffix_index < len(suffixes) - 1:
            size /= 1024
            suffix_index += 1
        return f"{size:.2f} {suffixes[suffix_index]}"

    total_size_str = convert_size(total_size)
    downloaded_size_str = convert_size(downloaded_size)
    duration_str = convert_duration(duration)

    time_per_byte = duration / downloaded_size if downloaded_size > 0 else 0
    estimated_time = int((total_size - downloaded_size) *
                         time_per_byte) if time_per_byte > 0 else 0
    estimated_time_str = convert_duration(estimated_time)
    return duration_str, total_size_str, downloaded_size_str, estimated_time_str
