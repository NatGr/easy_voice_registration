# Easy Voice Registration
This repo provides a small python script to register phrases from your microphone.

## Usage
```
python transcribe.py --csv example.csv --audio_folder audio_folder
```
csv is assumed to be a csv file of 2 columns (wav files names and the sentence they will contain, see example.csv).  
The script will ask the user to pronounce the sentence and save the result in the corresponding file name in wav format.  
If some of the files in the csv already exists in audio_folder, nothing is done. This allows to quit the program and resume where we were.  
Before writing a wav file, webrtcvad (a voice activity detector) is used to skip the silence at the start and end of the recording.  

The rate, n_channels, frames per buffer, whether to use (which strength of) vad or not and whether to randomly shuffle 
the order in which sentences must be pronounced can be specified as additional arguments.  

In case you commit an error while registering audio, you should:
  - end the registration
  - search for the most recently created audio file
  - delete the later
  - keep registering other files
  - relaunching the program, which will ask again for the badly registered file since it was deleted

## Installation
Requires Python 3.6+, additionally you will have to install portaudio, pyaduio (it's python bindings) and webrtcvad.  
To install portaudio, please look [here](http://www.portaudio.com/download.html). On macOs, you can also use brew
```
brew install portaudio
```

Then you need to install the python requirements
```
pip install -r requirements.txt
```
