from Components.YoutubeDownloader import download_youtube_video
from Components.Edit import extractAudio, crop_video
from Components.Transcription import transcribeAudio
from Components.LanguageTasks import GetHighlight
from Components.FaceCrop import crop_to_vertical, combine_videos

url = input("Enter YouTube video URL: ")
Vid= download_youtube_video(url)
if Vid:
    Vid = Vid.replace(".webm", ".mp4")
    print(f"Downloaded video and audio files successfully! at {Vid}")

    Audio = extractAudio(Vid)
    if Audio:

        transcriptions = transcribeAudio(Audio)
        if len(transcriptions) > 0:
            TransText = ""

            for text, start, end in transcriptions:
                TransText += (f"{start} - {end}: {text}")

            start , stop = GetHighlight(TransText)
            if start != 0 and stop != 0:
                print(f"Start: {start} , End: {stop}")

                Output = "Out.mp4"

                crop_video(Vid, Output, start, stop)
                croped = "croped.mp4"

                crop_to_vertical("Out.mp4", croped)
                combine_videos("Out.mp4", croped, "Final.mp4")
            else:
                print("Error in getting highlight")
        else:
            print("No transcriptions found")
    else:
        print("No audio file found")
else:
    print("Unable to Download the video")