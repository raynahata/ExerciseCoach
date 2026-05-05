# ExerciseCoach

ExerciseCoach is a Pepper robot exercise companion. It runs a short social intro, guides a participant through exercise sets, listens to the participant through AWS Transcribe, generates conversational replies with OpenAI, and sends speech, tablet text, eye color, arm motion, and recording commands to Pepper through ROS.

This project is research/prototype code. The most important thing to understand is that it intentionally mixes Python 3 and Python 2:

- Python 3 runs the conversation/session logic, AWS speech-to-text, OpenAI calls, and logging.
- Python 2.7 runs Pepper control through the NAOqi SDK.
- ROS Noetic connects the two sides with topics.

## Repository Map

```text
.
|-- README.md
|-- pynaoqi-python2.7-2.8.6.23-linux64-20191127_152327/
|   `-- Vendored NAOqi Python 2.7 SDK for Pepper
`-- scripts/SocialCoach-main/
    |-- pepper_social.py                      # Main exercise-session orchestrator, Python 3
    |-- pepper_intro.py                       # Intro conversation before exercise, Python 3
    |-- pepper_controller.py                  # Main Pepper ROS/NAOqi controller, Python 2.7
    |-- AWS_STT.py                            # AWS Transcribe streaming speech-to-text
    |-- conv_logger.py                        # CSV/plain-text conversation logging
    |-- config.example.yaml                   # Template for local config.yaml
    |-- summary_generator.py                  # Generates summaries from conversation CSVs
    |-- reset_page.py                         # Clears/resets Pepper tablet display
    |-- prompts/                              # Participant/week prompt templates
    |-- conversation_files/                   # Participant/week conversation logs
    |-- recordings/                           # Runtime recordings, ignored by git
    `-- archive/                              # Older controllers, experiments, and legacy docs
```

## How The System Works

The runtime is split into two ROS node families.

The Python 3 session scripts decide what should happen:

- `pepper_intro.py` runs a short conversation before the workout.
- `pepper_social.py` runs the exercise flow.
- Both scripts read an OpenAI key from `scripts/SocialCoach-main/chatGPT.key`.
- Both scripts call `AWS_STT.start_transcription()` to capture one user utterance at a time.
- Both scripts publish robot speech to `/gpt_speech`, display-only text to `/speech_display`, exercise commands to `/exercise_command`, and shutdown messages to `/controller_shutdown`.

The Python 2 Pepper controller executes those commands:

- `pepper_controller.py` subscribes to the session topics.
- It uses NAOqi `ALProxy` services for text-to-speech, tablet display, LEDs, arm motion, camera frames, and robot state.
- It publishes `/pepper/tts_status` so the Python 3 side knows when Pepper is still speaking.
- It publishes Pepper camera frames to `/pepper_camera/image_raw`.
- It records camera frames to ROS bag files and local microphone audio to WAV files under `scripts/SocialCoach-main/recordings/`.

Important ROS topics:

| Topic | Direction | Purpose |
| --- | --- | --- |
| `/gpt_speech` | Python 3 -> Python 2 | Text Pepper should say out loud and show on tablet |
| `/speech_display` | Python 3 -> Python 2 | Text Pepper should show on tablet only |
| `/exercise_command` | Python 3 -> Python 2 | Exercise motion command: `bicep curls`, `lateral raises`, or `rest` |
| `/controller_shutdown` | Python 3 -> Python 2 | Tells the controller to exit |
| `/pepper/tts_status` | Python 2 -> Python 3 | `True` while Pepper is speaking, `False` when done |
| `/pepper_camera/image_raw` | Python 2 -> ROS | Pepper camera image stream for recording |
| `pepper_state` | shared | Current coarse state, usually `speaking` or `listening` |

## Prerequisites

Install these on the computer that will run the session:

- ROS Noetic.
- Python 2.7 for NAOqi.
- Python 3 for AWS/OpenAI/session code.
- The NAOqi Python 2.7 SDK. A copy is already present in this repo under `pynaoqi-python2.7-2.8.6.23-linux64-20191127_152327/`.
- AWS CLI credentials configured for an account with Amazon Transcribe access.
- An OpenAI API key in `scripts/SocialCoach-main/chatGPT.key`.
- A working microphone for AWS Transcribe.
- Network access from the computer to Pepper on port `9559`.
- `arecord` on the controller machine if you want the local WAV recording path to work.

Python 3 package install, based on the imports in the current scripts:

```sh
python3 -m pip install openai amazon-transcribe sounddevice pandas pyyaml
```

The older/legacy scripts may also need:

```sh
python3 -m pip install pynput asyncio pvporcupine pyaudio gtts
```

For Python 2, make sure the NAOqi SDK is on `PYTHONPATH` before running controller scripts:

```sh
export PYTHONPATH="${PYTHONPATH}:$(pwd)/pynaoqi-python2.7-2.8.6.23-linux64-20191127_152327/lib/python2.7/site-packages"
```

The active Python 2 controller also imports `yaml`, so install PyYAML for the Python 2 environment if it is not already available.

## Configure Before A Session

Before running with a participant, check these items.

1. Create local config and set Pepper/study metadata.

   `config.yaml` is intentionally gitignored because it can contain local robot/network details and participant identifiers. Start by copying the example:

   ```sh
   cp scripts/SocialCoach-main/config.example.yaml scripts/SocialCoach-main/config.yaml
   ```

   Edit `scripts/SocialCoach-main/config.yaml`:

   ```yaml
   pepper_ip: "192.168.8.107"
   pepper_port: 9559
   participant_number: 21
   week_number: 3
   generate_summary_after_session: false
   summary_prompt_file: "summaryPrompt.txt"
   summary_model: "gpt-4o"
   summary_max_tokens: 250
   ```

   `pepper_controller.py`, `pepper_intro.py`, and `pepper_social.py` all read this file.

   Leave `generate_summary_after_session` set to `false` to skip automatic summary generation. Set it to `true` when you want `pepper_social.py` to generate a summary from the participant/week CSV after the exercise session ends.

2. Confirm prompts exist.

   Prompt files are gitignored because participant-specific prompts may contain names or other study details. Keep local prompt files under `scripts/SocialCoach-main/prompts/`.

   For week `0`, the exercise session uses:

   ```text
   scripts/SocialCoach-main/prompts/conversational_prompt_0.txt
   ```

   For later weeks, it uses:

   ```text
   scripts/SocialCoach-main/prompts/conversational_prompt_{participant_number}_week_{week_number}.txt
   ```

   The intro session uses:

   ```text
   scripts/SocialCoach-main/prompts/intro_prompt
   scripts/SocialCoach-main/prompts/intro_prompt_reccuring
   ```

3. Confirm `chatGPT.key` exists.

   Put the OpenAI key in:

   ```text
   scripts/SocialCoach-main/chatGPT.key
   ```

   This file is ignored by git and should not be committed.

4. Confirm AWS credentials.

   `AWS_STT.py` uses AWS Transcribe Streaming in region `us-east-2`. Make sure `aws configure` has valid credentials on the machine running the Python 3 scripts.

## Running The Study Flow

Open three terminals from the repo root.

### Terminal 1: Start ROS

```sh
roscore
```

### Terminal 2: Start Pepper Controller

```sh
export PYTHONPATH="${PYTHONPATH}:$(pwd)/pynaoqi-python2.7-2.8.6.23-linux64-20191127_152327/lib/python2.7/site-packages"
cd scripts/SocialCoach-main
python2 pepper_controller.py
```

Optional first step, if you need to clear Pepper's tablet:

```sh
python2 reset_page.py
```

### Terminal 3: Run The Intro, Then Exercise Session

```sh
cd scripts/SocialCoach-main
python3 pepper_intro.py
python3 pepper_social.py
```

The intro session ends when the prompt/parser decides the participant is ready. The exercise session asks the participant to say `ready`, then runs four sets:

1. Bicep curls
2. Bicep curls
3. Lateral raises
4. Lateral raises

Each set is currently timed for about 40 seconds, with about 40 seconds of rest between sets.

Say `bye` during the session to stop early.

## Runtime Outputs

Conversation logs are written to:

```text
scripts/SocialCoach-main/conversation_files/participant_{participant}_week_{week}.csv
scripts/SocialCoach-main/conversation_log.txt
```

Video ROS bags are written to:

```text
scripts/SocialCoach-main/recordings/
```

Local audio WAV files are also written to:

```text
scripts/SocialCoach-main/recordings/
```

The current filenames include participant, week, and timestamp:

```text
video_only_p{participant}_week{week}_{timestamp}.bag
local_audio_p{participant}_week{week}_{timestamp}.wav
```

Summaries from `summary_generator.py` are written to:

```text
scripts/SocialCoach-main/summaries/
```

These runtime folders are ignored by git in the top-level `.gitignore`.

## Conversation Summaries

Manual summary generation uses the participant/week values from `config.yaml`:

```sh
cd scripts/SocialCoach-main
python3 summary_generator.py
```

The script reads the participant/week CSV from `conversation_files/`, combines it with `prompts/summaryPrompt.txt`, asks OpenAI for a summary, and saves the result under `summaries/`.

Automatic summary generation is available but disabled by default. To turn it on for the end of `pepper_social.py`, set:

```yaml
generate_summary_after_session: true
```

The automatic path uses these optional config values:

```yaml
summary_prompt_file: "summaryPrompt.txt"
summary_model: "gpt-4o"
summary_max_tokens: 250
```

## Archived Files

The root of `scripts/SocialCoach-main/` is intentionally kept to the final "eyes" study path and shared helpers. Older study scripts, controller variants, one-off tests, and legacy docs live in:

```text
scripts/SocialCoach-main/archive/
```

Notable archived files include:

- `Open_ai_response.py`, the older full-loop script.
- `pepper_controller_jp.py`, an alternate controller with Pepper-side MP4 recording.
- `pepper_controller_eyes_no_local_audio.py`, the prior eyes controller before local WAV recording/config promotion.
- `listener.py`, `talker.py`, and `speech.py`, older ROS/audio helpers used by earlier flows.
- `video_test.py`, `eye_test.py`, `check_battery.py`, `peppergreet.py`, and `emotion_detection_log.py`, one-off Pepper test scripts.
- `README_legacy.md`, the old nested README from `scripts/SocialCoach-main/`.

## Common Issues

- `ImportError: No module named naoqi`: the NAOqi SDK path is missing from `PYTHONPATH`, or the controller is being run with Python 3 instead of Python 2.
- Pepper does not speak or move: check Pepper's IP address, network connectivity, and that port `9559` is reachable.
- Python 3 script hangs while listening: check microphone permissions, AWS credentials, and AWS Transcribe access in `us-east-2`.
- Prompt file not found: check the participant/week values and make sure the matching prompt exists under `prompts/`.
- Session logs go to the wrong file: check `participant_number` and `week_number` in `config.yaml` before starting.
- `rosbag` command not found: make sure ROS Noetic is installed and sourced in the controller terminal.
- Local audio file is missing: make sure `arecord` is installed and the controller machine has permission to access the microphone.

## Notes For Future Maintainers

- Secrets should stay out of git. `chatGPT.key` is ignored, but verify it has not been committed in older history before sharing the repo.
- The code currently has hardcoded timing, exercise order, model name (`gpt-4o`), and AWS region (`us-east-2`).
- Legacy scripts and older notes are archived rather than deleted so future maintainers can recover ideas without confusing them for the active run path.
