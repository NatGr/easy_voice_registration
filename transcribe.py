import argparse
import pyaudio
import csv
import sys
import os
import time
import wave
import webrtcvad
from typing import List
from random import shuffle


VAD_FRAME_DURATION_MS = 30


def in_red(arg: str) -> str:
    """returns arg surrounded with to print it in red on terminal"""
    return f"\x1b[0;31;48m{arg}\x1b[0m"


def process_audio(in_data, frame_count, time_info, status):
    frames.append(in_data)
    return in_data, pyaudio.paContinue


def reframe_audio(frame_duration_ms: int, audio: bytes, sample_rate: int) -> List[bytes]:
    """
    Cuts the audio in frames of the requested duration.
    Return the cut frames within a list (last incomplete frame is not returned)
    """
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    return [audio[offset:offset + n] for offset in range(0, len(audio) - n, n)]


def vad_filter(sample_rate: int, vad: webrtcvad.Vad, frames: List[bytes]) -> bytes:
    """
    # Adapted from https://github.com/wiseman/py-webrtcvad/blob/3b39545dbb026d998bf407f1cb86e0ed6192a5a6/example.py#L45
    Filters out non-voiced audio frames.
    Given a webrtcvad.Vad and a source of audio frames, returns the voiced audio.
    Uses a padded, sliding window algorithm over the audio frames.
    All frames between [prev(first(speech_frame)), next(last(speech_frame))] will be considered as speech frames.
    This is done because we want to remove leading and tailing silence here.
    Arguments:
    sample_rate - The audio sample rate, in Hz.
    vad - An instance of webrtcvad.Vad.
    frames - a source of audio frames.
    Returns: the speech withing the frames.
    """
    voiced_frames_offsets = [i for i, frame in enumerate(frames) if vad.is_speech(frame, sample_rate)]
    if len(voiced_frames_offsets) > 0:
        return b''.join(frames[max(voiced_frames_offsets[0] - 1, 0) : min(voiced_frames_offsets[-1] + 2, len(frames))])
        # + 2 because b is not included in list[a:b]
    else:
        return b''.join(frames)


if __name__ == '__main__':
    parser = argparse.ArgumentParser("""Transcribes speaker data""")
    parser.add_argument("--csv", help="name of the csv file containing file names and sentences",
                        required=True)
    parser.add_argument("--audio_folder", help="name of the folder that will contain the transcribed wav files",
                        required=True)
    parser.add_argument("--rate", type=int, default=16000,
                        help="rate of the audio recording, webrtcvad only works with 8000, 16000, 32000 or 48000 Hz")
    parser.add_argument("--n_channels", type=int, default=1,
                        help="number of channels in the audio recording, webrtcvad only works with 1 channel")
    parser.add_argument("--frames_per_buffer", help="number of frames per buffer in the audio recording", type=int,
                        default=1024)
    parser.add_argument("--no_vad", help="deactivate trimming silence within audio", action='store_true')
    parser.add_argument("--vad_aggressiveness", choices=(1, 2, 3), default=2,
                        help="aggressiveness of the voice detection, the higher the more likely we are to trim speech")
    parser.add_argument("--random_order", action='store_true',
                        help="will ask you to pronounce the sentence in random order to be a bit less monotone")
    args = parser.parse_args()

    # reads csv
    with open(args.csv) as file:
        csv_reader = csv.reader(file, delimiter=',')
        row = next(csv_reader)

        if len(row) != 2 or row[0] != "file" or row[1] != "sentence":
            sys.stderr.write("csv header should be 'file,sentence', see example.csv\n")
            sys.exit(-1)

        data = [(f"{row[0]}.wav", row[1]) for row in csv_reader]

    if args.random_order:
        shuffle(data)

    # finds already created files
    if os.path.exists(args.audio_folder):
        already_created = set(os.listdir(args.audio_folder))
    else:
        os.mkdir(args.audio_folder)
        already_created = set()

    pyaudio_audio = pyaudio.PyAudio()
    stream = pyaudio_audio.open(format=pyaudio.paInt16, channels=args.n_channels, rate=args.rate, input=True,
        frames_per_buffer=args.frames_per_buffer, stream_callback=process_audio)

    # queries user for each row
    for file, sentence in data:
        if file in already_created:
            print(f"sentence {in_red(sentence)} was already spoken")
        else:

            frames = []
            print(f"Sentence to pronounce: {in_red(sentence)}")
            try:
                input('Please press enter to start speaking, when done speaking or to quit now, press Ctrl-C')
            except KeyboardInterrupt:
                exit(0)

            # reads stream
            stream.start_stream()
            try:
                while stream.is_active():
                    time.sleep(0.1)
            except KeyboardInterrupt:
                stream.stop_stream()

            audio = b''.join(frames)

            # trims the audio
            if not args.no_vad and args.n_channels == 1 and args.rate in (8000, 16000, 32000, 48000):
                audio = vad_filter(args.rate, vad=webrtcvad.Vad(args.vad_aggressiveness),
                                   frames=reframe_audio(VAD_FRAME_DURATION_MS, audio, args.rate))

            # writes wav
            waveFile = wave.open(os.path.join(args.audio_folder, file), 'wb')
            waveFile.setnchannels(args.n_channels)
            waveFile.setsampwidth(pyaudio_audio.get_sample_size(pyaudio.paInt16))
            waveFile.setframerate(args.rate)
            waveFile.writeframes(audio)
            waveFile.close()
        print("------")