// Twilio Media Streams <-> STT -> Claude -> TTS bridge (outline, not production code).
// Node 22, `ws`, Deepgram streaming STT (Flux or Nova-3), Cartesia or ElevenLabs streaming TTS.
// One process per region; one WebSocket per call. Twilio sends 20 ms frames of
// audio/x-mulaw 8000 Hz mono, base64, inside JSON messages.
//
// Inbound message events from Twilio: connected, start, media, dtmf, mark, stop.
// Outbound messages to Twilio:        media (play audio), mark (get notified when
//                                      played), clear (flush buffered audio = barge-in).
//
// TwiML that starts the stream (returned from the call's webhook after the
// disclosure <Say> and consent capture, see automation.html section 3):
//   <Response><Connect><Stream url="wss://voice.zm.example/twilio">
//     <Parameter name="call_id" value="cal_01J..."/>
//   </Stream></Connect></Response>

import { WebSocketServer, WebSocket } from "ws";
import { createSttStream, createTtsStream } from "./vendors";          // thin wrappers, not shown
import { runTurn } from "./voice-agent";                                // Claude call with tools, not shown
import { audit, emit } from "./bus";                                    // audit log + event bus, not shown

type TwilioMsg =
  | { event: "connected"; protocol: string; version: string }
  | { event: "start"; streamSid: string; start: { callSid: string; customParameters: Record<string, string>; mediaFormat: { encoding: string; sampleRate: number; channels: number } } }
  | { event: "media"; streamSid: string; media: { track: string; chunk: string; timestamp: string; payload: string } }
  | { event: "dtmf"; streamSid: string; dtmf: { digit: string } }
  | { event: "mark"; streamSid: string; mark: { name: string } }
  | { event: "stop"; streamSid: string };

const wss = new WebSocketServer({ port: 8081, path: "/twilio" });
// Production: validate the X-Twilio-Signature header on the upgrade request.

wss.on("connection", (twilio: WebSocket) => {
  let streamSid = "";
  let callId = "";
  let speaking = false;                 // true while TTS audio is queued at Twilio
  let turnAbort: AbortController | null = null;
  const transcript: { role: "agent" | "supplier"; text: string; t: number }[] = [];

  // STT: send mulaw straight through (Deepgram accepts encoding=mulaw&sample_rate=8000),
  // no resampling hop. Use the vendor's end-of-turn signal (Flux) or VAD + endpointing (Nova-3).
  const stt = createSttStream({ encoding: "mulaw", sampleRate: 8000, interim: true });

  // TTS: request ulaw_8000 output so frames can go to Twilio without transcoding.
  const tts = createTtsStream({ outputFormat: "ulaw_8000" });

  function sendAudio(b64: string) {
    twilio.send(JSON.stringify({ event: "media", streamSid, media: { payload: b64 } }));
  }
  function bargeIn() {
    // Supplier started talking over the agent: flush Twilio's buffer, cancel TTS and LLM.
    if (!speaking) return;
    twilio.send(JSON.stringify({ event: "clear", streamSid }));
    tts.cancel();
    turnAbort?.abort();
    speaking = false;
    emit("zm.call.barge_in.v1", { callId });
  }

  stt.on("speech_started", bargeIn);               // VAD start-of-speech
  stt.on("interim", (_text: string) => bargeIn()); // belt and braces: any interim words
  stt.on("end_of_turn", async (text: string) => {
    transcript.push({ role: "supplier", text, t: Date.now() });
    turnAbort = new AbortController();
    // runTurn streams Claude's text; sentence-chunk it into TTS so audio starts
    // on the first clause, not after the full reply.
    for await (const chunk of runTurn({ callId, transcript, signal: turnAbort.signal })) {
      if (chunk.type === "text") { speaking = true; tts.push(chunk.text); }
      if (chunk.type === "tool" && chunk.name === "transfer_to_human") {
        await tts.flush();
        return warmTransfer(callId, chunk.input);  // see below
      }
      if (chunk.type === "tool" && chunk.name === "end_call") { await tts.flush(); return hangup(callId); }
    }
    await tts.flush();
    twilio.send(JSON.stringify({ event: "mark", streamSid, mark: { name: `turn-${transcript.length}` } }));
  });
  tts.on("audio", (ulawB64: string) => sendAudio(ulawB64));

  twilio.on("message", (raw) => {
    const msg = JSON.parse(raw.toString()) as TwilioMsg;
    switch (msg.event) {
      case "start":
        streamSid = msg.streamSid;
        callId = msg.start.customParameters.call_id;
        audit({ action: "call.stream_start", subject: callId, data: { callSid: msg.start.callSid } });
        break;
      case "media":
        stt.write(Buffer.from(msg.media.payload, "base64"));
        break;
      case "mark":
        speaking = false;                         // Twilio finished playing our audio
        break;
      case "dtmf":
        if (msg.dtmf.digit === "0") warmTransfer(callId, { reason: "callee pressed 0" });
        break;
      case "stop":
        stt.close(); tts.close();
        emit("zm.call.ended.v1", { callId, transcript });   // Quality/Comms agent extracts commitments
        break;
    }
  });
});

// Warm transfer: move the PSTN leg into a Conference, dial the on-call human into
// the same conference with a whisper (agent-generated brief read only to the human),
// keep the AI leg muted or drop it once the human joins. Uses the Twilio REST API:
//   1. calls(callSid).update({ twiml: '<Response><Dial><Conference ...>cal_01J...</Conference></Dial></Response>' })
//   2. conferences(name).participants.create({ from, to: humanNumber, earlyMedia: true,
//        url: whisperTwimlUrl })   // <Say> brief to the human before bridging
//   3. on participant-join callback: say "Connecting you with Dana from Zine Machine" to the supplier.
async function warmTransfer(callId: string, input: { reason: string }) { /* ... */ }
async function hangup(callId: string) { /* calls(callSid).update({ status: "completed" }) */ }
