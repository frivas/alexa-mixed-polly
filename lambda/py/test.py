from mutagen.mp3 import MP3
from pydub import AudioSegment

import os, boto3

defaultRegion = 'eu-west-1'
defaultUrl = 'https://polly.eu-west-1.amazonaws.com/'
bucketName = 'mixedpolly'
backgroundfile = 'audio/pavane2.mp3'

def connectToPolly(regionName=defaultRegion, endpointUrl=defaultUrl):
    return boto3.client('polly', region_name=regionName, endpoint_url=endpointUrl)

def combine_files(polyfile, backgroundfile, duration):
    voice = AudioSegment.from_mp3(polyfile)
    background = AudioSegment.from_mp3(backgroundfile)
    result = voice + background
    result.export('audio/result.mp3', format='mp3')


def speak(polly, text, format='mp3', voice='Lucia'):
    resp = polly.synthesize_speech(OutputFormat=format, Text=text, VoiceId=voice)
    soundfile = open('audio/sound.mp3', 'wb')
    soundBytes = resp['AudioStream'].read()
    soundfile.write(soundBytes)
    soundfile.close()
    os.system('afplay audio/sound.mp3')  # Works only on Mac OS, sorry
    audio = MP3("audio/sound.mp3")
    audio_length = audio.info.length
    combine_files('audio/sound.mp3', backgroundfile)
    # os.remove('audio/sound.mp3')
    os.system('afplay audio/result.mp3')  # Works only on Mac OS, sorry


polly = connectToPolly()
speak(polly, "Hola, bienvenidos al Teatro Real. Te traermos la mas amplia variedad de Opera")
