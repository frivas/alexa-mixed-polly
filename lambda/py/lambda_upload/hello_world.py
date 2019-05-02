# -*- coding: utf-8 -*-

# This is a simple Hello World Alexa Skill, built using
# the implementation of handler classes approach in skill builder.
import logging
import os
import boto3
import subprocess
import hashlib

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.utils.request_util import get_slot_value
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model.ui import SimpleCard
from ask_sdk_model import Response
from ask_sdk_core.response_helper import get_plain_text_content

from mutagen.mp3 import MP3

import gender_guesser.detector as gender

s3 = boto3.resource('s3')
sb = SkillBuilder()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

my_region = 'eu-west-1'
bucket_name = 'mixedpolly'
polly_url = f'https://polly.{my_region}.amazonaws.com/'
s3_url = f'https://s3-{my_region}.amazonaws.com/'
background_file_intro = f"{os.environ['LAMBDA_TASK_ROOT']}/audio/pavane_aws.mp3"
hello_file = f"{os.environ['LAMBDA_TASK_ROOT']}/audio/inspirational_aws.mp3"


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        prepareTools()

        polly = connectToPolly()

        polly_mix_result = generatePollyMix(polly, "Hola, bienvenidos a esta skill de ejemplo. Prueba decirme nombres de chico y chica y eso determinará la voz que utilizaré", 'Lucia', background_file_intro)

        audio_mix = getS3AudioFile()

        speech_text = f"<speak> Esto es Poly {audio_mix} Dime un numbre</speak>"
        logger.info(speech_text)
        logger.info(get_plain_text_content(primary_text=speech_text))

        handler_input.response_builder.speak(speech_text).set_should_end_session(False)
        return handler_input.response_builder.response


class HelloWorldIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("HelloWorldIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        polly = connectToPolly()

        gender_detector = gender.Detector()

        get_name = get_slot_value(handler_input, 'name')
        logger.info(f"NAME {get_name}")

        get_gender = gender_detector.get_gender(get_name.capitalize())
        logger.info(f"GENDER {get_gender}")

        polly_mixed_result = generatePollyMix(polly, f"usar Poly en tu Skill te permite ofrecer una experiencia única.", 'Enrique' if get_gender == 'male' else 'Lucia', hello_file)

        audio_mix = getS3AudioFile()

        speech_text = f"<speak>{get_name.capitalize()}, {audio_mix}</speak>"

        handler_input.response_builder.speak(speech_text).set_should_end_session(True)
        return handler_input.response_builder.response


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speech_text = "You can say hello to me!"

        handler_input.response_builder.speak(speech_text).ask(
            speech_text).set_card(SimpleCard(
                "Hello World", speech_text))
        return handler_input.response_builder.response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speech_text = "Goodbye!"

        handler_input.response_builder.speak(speech_text).set_card(
            SimpleCard("Hello World", speech_text))
        return handler_input.response_builder.response


class FallbackIntentHandler(AbstractRequestHandler):
    """AMAZON.FallbackIntent is only available in en-US locale.
    This handler will not be triggered except in that locale,
    so it is safe to deploy on any locale.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speech_text = (
            "The Hello World skill can't help you with that.  "
            "You can say hello!!")
        reprompt = "You can say hello!!"
        handler_input.response_builder.speak(speech_text).ask(reprompt)
        return handler_input.response_builder.response


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Catch all exception handler, log exception and
    respond with custom message.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speech = "Sorry, there was some problem. Please try again!!"
        handler_input.response_builder.speak(speech).ask(speech)

        return handler_input.response_builder.response


def prepareTools():
    exists = os.path.isfile('/tmp/sox')
    if not exists:
        logger.info('FILE DOES NOT EXISTS')
        cp_cmd_output = subprocess.run([f"cp {os.environ['LAMBDA_TASK_ROOT']}/audio/sox /tmp; chmod 755 /tmp/sox"], shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
        logger.info(f"CP {cp_cmd_output}")


def connectToPolly(regionName=my_region, endpointUrl=polly_url):
    return boto3.client('polly', region_name=regionName, endpoint_url=endpointUrl)


def generatePollyMix(polly, text, voice, backgroundSFX, format='mp3'):
    resp = polly.synthesize_speech(OutputFormat=format, Text=text, VoiceId=voice)
    soundfile = open(f"/tmp/sound.mp3", 'wb')
    soundBytes = resp['AudioStream'].read()
    soundfile.write(soundBytes)
    soundfile.close()

    audio = MP3("/tmp/sound.mp3")
    audio_length = audio.info.length

    sox_cmd = f"/tmp/sox -m {backgroundSFX} /tmp/sound.mp3 -C 48.01 /tmp/output.mp3 rate 22050 gain -l 16 trim 0 {audio_length + 4}"

    sox_cmd_output = subprocess.run([sox_cmd], shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)

    # list = f"ls -larth {os.environ['LAMBDA_TASK_ROOT']}/audio/"
    # list_tmp = f"{background_file_intro}"

    # ls_cmd_output = subprocess.run([list], shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    # ls_tmp_cmd_output = subprocess.run([list_tmp], shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    # logger.info(f'LIST {ls_cmd_output}')
    # logger.info(f'SOX {sox_cmd_output}')
    # logger.info(f'TMP {ls_tmp_cmd_output}')

    return sox_cmd_output.returncode

def getS3AudioFile():
    s3_filename = hashlib.md5(open('/tmp/output.mp3', 'rb').read()).hexdigest() + '.mp3'
    s3.Bucket(bucket_name).upload_file(Filename='/tmp/output.mp3', Key=s3_filename, ExtraArgs={'ACL':'public-read'})

    os.remove('/tmp/sound.mp3')
    os.remove('/tmp/output.mp3')
    return f'<audio src="{s3_url}{bucket_name}/{s3_filename}"/>'


sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(HelloWorldIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

sb.add_exception_handler(CatchAllExceptionHandler())

handler = sb.lambda_handler()
