import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger


from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.google.tts import GoogleTTSService
from pipecat.transcriptions.language import Language

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import BotInterruptionFrame, EndFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.services.groq.llm import GroqLLMService
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.network.websocket_server import (
    WebsocketServerParams,
    WebsocketServerTransport,
)

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


class SessionTimeoutHandler:
    """Handles actions to be performed when a session times out.
    Inputs:
    - task: Pipeline task (used to queue frames).
    - tts: TTS service (used to generate speech output).
    """

    def __init__(self, task, tts):
        self.task = task
        self.tts = tts
        self.background_tasks = set()

    async def handle_timeout(self, client_address):
        """Handles the timeout event for a session."""
        try:
            logger.info(f"Connection timeout for {client_address}")

            # Queue a BotInterruptionFrame to notify the user
            await self.task.queue_frames([BotInterruptionFrame()])

            # Send the TTS message to inform the user about the timeout
            await self.tts.say(
                "I'm sorry, we are ending the call now. Please feel free to reach out again if you need assistance."
            )

            # Start the process to gracefully end the call in the background
            end_call_task = asyncio.create_task(self._end_call())
            self.background_tasks.add(end_call_task)
            end_call_task.add_done_callback(self.background_tasks.discard)
        except Exception as e:
            logger.error(f"Error during session timeout handling: {e}")

    async def _end_call(self):
        """Completes the session termination process after the TTS message."""
        try:
            # Wait for a duration to ensure TTS has completed
            await asyncio.sleep(15)

            # Queue both BotInterruptionFrame and EndFrame to conclude the session
            await self.task.queue_frames([BotInterruptionFrame(), EndFrame()])

            logger.info("TTS completed and EndFrame pushed successfully.")
        except Exception as e:
            logger.error(f"Error during call termination: {e}")


async def main():
    transport = WebsocketServerTransport(
        params=WebsocketServerParams(
            serializer=ProtobufFrameSerializer(),
            audio_out_enabled=True,
            add_wav_header=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
            session_timeout=60 * 3,  # 3 minutes
        )
    )

    #llm = OpenAILLMService(api_key="open_AI_key",model="gpt-4o-mini")
    llm = GroqLLMService(api_key=os.getenv("GROQ_API_KEY"))


    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    tts = CartesiaTTSService(
        
        api_key=os.getenv("CARTESIA_aPI_KEY"),
        # voice_id="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
        voice_id="28ca2041-5dda-42df-8123-f58ea9c3da00" # Arushi Indian
    )
    # tts = DeepgramTTSService(
    #     api_key=os.getenv("DEEPGRAM_API_KEY"),
    #     # voice="aura-helios-en",
    #     voice="aura-2-aurora-en",
    #     sample_rate=16000
    # )

    # tts = GoogleTTSService(
    #     voice_id="en-US-Chirp3-HD-Charon",
    #     params=GoogleTTSService.InputParams(language=Language.EN_US),
    #     credentials=""
    # )

    # tts._settings = {
    #         "speed": 1.0
    #         }

    messages = [
        {
            "role": "system",
            "content": (
                "You are a friendly and helpful assistant in a voice call. "
                "Speak naturally, clearly, and concisely. "
                "Keep your responses precise and easy to understand. "
                "Do not include special characters or punctuation that can't be spoken. "
                "When the call starts, greet the user warmly and make them feel welcome. "
                "Respond to the user creatively and helpfully, like a human conversation."
            ),

        },
    ]

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),  # Websocket input from client
            stt,  # Speech-To-Text
            context_aggregator.user(),
            llm,  # LLM
            tts,  # Text-To-Speech
            transport.output(),  # Websocket output to client
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=16000,
            allow_interruptions=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Kick off the conversation.
        messages.append({"role": "system", "content": "Please introduce yourself to the user."})
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler("on_session_timeout")
    async def on_session_timeout(transport, client):
        logger.info(f"Entering in timeout for {client.remote_address}")

        timeout_handler = SessionTimeoutHandler(task, tts)

        await timeout_handler.handle_timeout(client)

    runner = PipelineRunner()

    await runner.run(task)


if __name__ == "__main__":

    asyncio.run(main())
