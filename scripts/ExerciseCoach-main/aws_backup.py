# Base code credit: https://www.youtube.com/watch?v=_q5vBvTNDEA 
#this code will continually run the transcrption 
#NOTE this code cannot be used with the open ai code 
import asyncio
import sounddevice
from pynput import keyboard  # Requires 'pip install pynput'
import time
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent


# Global flag that controls the pause state
pause_transcription = False
space_pressed = False  # Track whether the space key is currently pressed

class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, output_stream):
        super().__init__(output_stream)
        self.transcribed_text = []  # Buffer to store full sentences
        self.partial_sentence = ""  # Buffer for accumulating partial sentence
        self.last_update_time = time.time()  # Track the time of the last transcript event
        self.silence_threshold = 1  # Threshold in seconds to detect pauses

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            if result.is_partial:
                continue 
            for alt in result.alternatives:
                text = alt.transcript
                self.partial_sentence += text + " "
                self.last_update_time = time.time()

    def get_full_transcription(self):
        # Return the full transcription
        return " ".join(self.transcribed_text)

    async def check_for_silence(self):
        # Check for pauses in transcription and print full sentences when detected
        while True:
            current_time = time.time()
            time_since_last_update = current_time - self.last_update_time
            
            # If the time since the last update exceeds the silence threshold
            if time_since_last_update >= self.silence_threshold and self.partial_sentence:
                # Consider the sentence complete, print it, and clear the buffer
                print(f"Full sentence: {self.partial_sentence.strip()}")
                
                # Append the sentence to the full transcription buffer
                self.transcribed_text.append(self.partial_sentence.strip())
                
                # Clear the partial sentence buffer
                self.partial_sentence = ""
            
            await asyncio.sleep(0.5)  # Check every 500ms


async def mic_stream():
    # This function wraps the raw input stream from the microphone forwarding
    # the blocks to an asyncio.Queue.
    loop = asyncio.get_event_loop()
    input_queue = asyncio.Queue()

    def callback(indata, frame_count, time_info, status):
        loop.call_soon_threadsafe(input_queue.put_nowait, (bytes(indata), status))

    # Be sure to use the correct parameters for the audio stream that matches
    # the audio formats described for the source language you'll be using:
    # https://docs.aws.amazon.com/transcribe/latest/dg/streaming.html
    stream = sounddevice.RawInputStream(
        channels=1,
        samplerate=16000,
        callback=callback,
        blocksize=1024 * 2,
        dtype="int16",
    )
    # Initiate the audio stream and asynchronously yield the audio chunks
    # as they become available.
    with stream:
        while True:
            indata, status = await input_queue.get()
            yield indata, status


async def write_chunks(stream):
    # This connects the raw audio chunks generator coming from the microphone
    # and passes them along to the transcription stream.
    global pause_transcription
    async for chunk, status in mic_stream():
        if pause_transcription:
            # Skip sending audio while paused
            await asyncio.sleep(0.1)  # Wait while paused, skipping audio
            continue
        await stream.input_stream.send_audio_event(audio_chunk=chunk)
    await stream.input_stream.end_stream()


async def basic_transcribe():
    # Set up our client with the chosen AWS region
    client = TranscribeStreamingClient(region="us-east-2")

    # Start transcription to generate our async stream
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm"
    )

    # Instantiate our handler and start processing events
    handler = MyEventHandler(stream.output_stream)
    await asyncio.gather(
        write_chunks(stream), 
        handler.handle_events(), 
        handler.check_for_silence()  # Run the silence detection loop
    )


def on_press(key):
    global pause_transcription, space_pressed
    try:
        if key == keyboard.Key.space and not space_pressed:
            pause_transcription = True
            space_pressed = True  # Mark the space key as pressed
            print("Space key pressed: Pausing transcription.")
    except AttributeError:
        pass


def on_release(key):
    global pause_transcription, space_pressed
    if key == keyboard.Key.space and space_pressed:
        pause_transcription = False
        space_pressed = False  # Mark the space key as released
        print("Space key released: Resuming transcription.")


def start_key_listener():
    # This function starts a listener for key press events.
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()


async def main():
    # Start key listener in the background
    start_key_listener()
    
    # Run transcription and key listener in parallel
    await basic_transcribe()


# Start the event loop
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()