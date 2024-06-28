from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.editor import VideoFileClip
import subprocess

# def crop_video(input_file, output_file, start_time, end_time):
#     command = f"ffmpeg -i {input_file} -ss {start_time} -to {end_time} -c copy {output_file}"
#     subprocess.call(command, shell=True)
#     print("done")


def extractAudio(video_path):
    try:
        video_clip = VideoFileClip(video_path)
        audio_path = "audio.wav"
        video_clip.audio.write_audiofile(audio_path)
        video_clip.close()
        print(f"Extracted audio to: {audio_path}")
        return audio_path
    except Exception as e:
        print(f"An error occurred while extracting audio: {e}")
        return None


def crop_video(input_file, output_file, start_time, end_time):
    with VideoFileClip(input_file) as video:
        cropped_video = video.subclip(start_time, end_time)
        cropped_video.write_videofile(output_file, codec='libx264')

# Example usage:
if __name__ == "__main__":
    input_file = r"videos\8888b955-21e9-4e59-b285-bf07437f76b9-input-file.mp4"
    print(input_file)
    output_file = "Short.mp4"
    start_time = 31.92 
    end_time = 49.2   

    crop_video(input_file, output_file, start_time, end_time)
    # input = r"videos\8888b955-21e9-4e59-b285-bf07437f76b9-input-file.mp4 "
    # print(extractAudio(input))
