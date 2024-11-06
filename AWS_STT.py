import asyncio
import sounddevice as sd
import time
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, output_stream):
        super().__init__(output_stream)
        self.partial_sentence = ""
        self.last_update_time = time.time()
        self.silence_threshold = 1  # Threshold in seconds to detect pauses

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            if result.is_partial:
                continue
            for alt in result.alternatives:
                text = alt.transcript
                #print(f"Received text: {text}")
                self.partial_sentence += text + " "
                self.last_update_time = time.time()

    async def check_for_silence(self):
        # Check for pauses and return full sentence when detected
        while True:
            time_since_last_update = time.time() - self.last_update_time
            if time_since_last_update >= self.silence_threshold and self.partial_sentence:
                full_sentence = self.partial_sentence.strip()
                self.partial_sentence = ""
                return full_sentence  # Return the detected sentence
            await asyncio.sleep(0.5)

async def mic_stream():
    loop = asyncio.get_event_loop()
    input_queue = asyncio.Queue()

    def callback(indata, frame_count, time_info, status):
        loop.call_soon_threadsafe(input_queue.put_nowait, (bytes(indata), status))

    stream = sd.RawInputStream(
        channels=1,
        samplerate=16000,
        callback=callback,
        blocksize=1024 * 2,
        dtype="int16"
    )
    with stream:
        while True:
            indata, status = await input_queue.get()
            yield indata, status

async def write_chunks(stream, stop_event):
    async for chunk, status in mic_stream():
        if stop_event.is_set():
            break
        if chunk:
            await stream.input_stream.send_audio_event(audio_chunk=chunk)
    await stream.input_stream.end_stream()

async def start_transcription():
    client = TranscribeStreamingClient(region="us-east-2")
    stream = await client.start_stream_transcription(
        language_code="en-US",
        media_sample_rate_hz=16000,
        media_encoding="pcm"
    )
    handler = MyEventHandler(stream.output_stream)

    # Create an event to signal stopping the audio stream
    stop_event = asyncio.Event()

    # Run transcription tasks in parallel
    write_task = asyncio.create_task(write_chunks(stream, stop_event))
    event_task = asyncio.create_task(handler.handle_events())
    silence_task = asyncio.create_task(handler.check_for_silence())

    # Wait for the first sentence to be detected
    full_sentence = await silence_task
    
    # Signal end of audio streaming and await task completion
    stop_event.set()
    await write_task  # Wait for write_chunks to complete
    await event_task  # Wait for handle_events to complete

    #print("Transcription complete.")
    return full_sentence  # Return the detected sentence

if __name__ == "__main__":
    asyncio.run(start_transcription())
# import asyncio
# import sounddevice as sd
# import time
# from amazon_transcribe.client import TranscribeStreamingClient
# from amazon_transcribe.handlers import TranscriptResultStreamHandler
# from amazon_transcribe.model import TranscriptEvent

# # Global flag that controls the pause state
# pause_transcription = False
# space_pressed = False  # Track whether the space key is currently pressed

# class MyEventHandler(TranscriptResultStreamHandler):
#     def __init__(self, output_stream):
#         super().__init__(output_stream)
#         self.transcribed_text = []  # Buffer to store full sentences
#         self.partial_sentence = ""  # Buffer for accumulating partial sentence
#         self.last_update_time = time.time()  # Track the time of the last transcript event
#         self.silence_threshold = 1  # Threshold in seconds to detect pauses

#     async def handle_transcript_event(self, transcript_event: TranscriptEvent):
#         results = transcript_event.transcript.results
#         for result in results:
#             if result.is_partial:
#                 continue 
#             for alt in result.alternatives:
#                 text = alt.transcript
#                 print(f"Received text: {text}")  # Debug print
#                 self.partial_sentence += text + " "
#                 self.last_update_time = time.time()

#     def get_full_transcription(self):
#         # Return the full transcription
#         return " ".join(self.transcribed_text)

#     async def check_for_silence(self):
#         # Check for pauses in transcription and print full sentences when detected
#         # while True:
#         #     current_time = time.time()
#         #     time_since_last_update = current_time - self.last_update_time
            

#         #     # If the time since the last update exceeds the silence threshold
#         #     if time_since_last_update >= self.silence_threshold and self.partial_sentence:
              
#         #         completed_sentence = self.partial_sentence.strip()
#         #         print(f"Full sentence detected: {completed_sentence}")  # Debug print
#         #         self.transcribed_text.append(completed_sentence)
#         #         self.partial_sentence = ""  # Clear the buffer
#         #         return completed_sentence  # Return the detected sentence

#         #     await asyncio.sleep(0.5)  # Check every 500ms
#         while True:
#             time_since_last_update = time.time() - self.last_update_time
#             if time_since_last_update >= self.silence_threshold and self.partial_sentence:
#                 # Complete the sentence and clear the buffer
#                 full_sentence = self.partial_sentence.strip()
#                 self.partial_sentence = ""
#                 return full_sentence  # Return the detected full sentence
#             await asyncio.sleep(0.5)

# async def mic_stream():
#     # loop = asyncio.get_event_loop()
#     # input_queue = asyncio.Queue()

#     # def callback(indata, frame_count, time_info, status):
#     #     if status:
#     #         print(f"Input status: {status}")
#     #     #print("Captured audio chunk")  # Debug print
#     #     loop.call_soon_threadsafe(input_queue.put_nowait, (bytes(indata), status))

#     # stream = sd.RawInputStream(
#     #     channels=1,
#     #     samplerate=16000,
#     #     callback=callback,
#     #     blocksize=1024 * 2,
#     #     dtype="int16"
#     # )
#     # with stream:
#     #     while True:
#     #         indata, status = await input_queue.get()
#     #         yield indata, status
#     loop = asyncio.get_event_loop()
#     input_queue = asyncio.Queue()

#     def callback(indata, frame_count, time_info, status):
#         loop.call_soon_threadsafe(input_queue.put_nowait, (bytes(indata), status))

#     stream = sd.RawInputStream(
#         channels=1,
#         samplerate=16000,
#         callback=callback,
#         blocksize=1024 * 2,
#         dtype="int16"
#     )
#     with stream:
#         while True:
#             indata, status = await input_queue.get()
#             yield indata, status

# async def write_chunks(stream):
#     async for chunk, status in mic_stream():
#         if chunk:
#             await stream.input_stream.send_audio_event(audio_chunk=chunk)
#     await stream.input_stream.end_stream()

# async def start_transcription():
#     client = TranscribeStreamingClient(region="us-east-2")
#     stream = await client.start_stream_transcription(
#         language_code="en-US",
#         media_sample_rate_hz=16000,
#         media_encoding="pcm"
#     )
#     handler = MyEventHandler(stream.output_stream)
    
#     print("Listening for input...")  # Debug print
#     handler = MyEventHandler(stream.output_stream)
#     # transcription_result=await asyncio.gather(
#     #     write_chunks(stream), 
#     #     handler.handle_events(), 
#     #     handler.check_for_silence()  # Run the silence detection loop
#     # )
#     transcription_result = await handler.check_for_silence()

#     print("Transcription complete.")  # Debug print
#     print(transcription_result) 
#     return transcription_result  # Return the transcribed sentence
# #sys.exit()

# # # Run the event loop only if this file is executed directly
# # if __name__ == "__main__":
# #     loop = asyncio.get_event_loop()
# #     try:
# #         result = loop.run_until_complete(start_transcription())
# #         print(f"Final transcription result: {result}")  # Print the final result
# #     except KeyboardInterrupt:
# #         print("\nTranscription interrupted.")
# #     finally:
# #         loop.close()

# if __name__ == "__main__":
#     asyncio.run(start_transcription())