// speech.js

let recognition = null;
let transcriptBox = null;
let finalText = "";
let isRecording = false;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

export function setupSpeechRecognition(textareaElement) {
    transcriptBox = textareaElement;

    if (!SpeechRecognition) {
        console.warn("Speech recognition not supported.");
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
        let interimText = "";

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            const text = result[0].transcript;

            if (result.isFinal) {
                finalText += `${text} `;
            } else {
                interimText += text;
            }
        }

        transcriptBox.value = finalText + interimText;
    };

    recognition.onend = () => {
        if (isRecording) {
            recognition.start();
        }
    };
}

export function startRecording() {
    if (!recognition) return;

    finalText = "";
    transcriptBox.value = "";
    isRecording = true;

    recognition.start();
}

export function pauseOrStopRecording() {
    if (!recognition) return;

    isRecording = false;
    recognition.stop();
}

export function resetRecording() {
    finalText = "";
    isRecording = false;

    if (recognition) {
        recognition.stop();
    }

    if (transcriptBox) {
        transcriptBox.value = "";
    }
}