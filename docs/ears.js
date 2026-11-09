// Gemini ears: records the microphone as 16 kHz mono WAV and stops when you stop talking.
// Used when Safari's own speech recognition can't run (for example in the iPad Home Screen app). The audio is only held
// in memory, sent to Gemini to be turned into text, and then dropped.

const TARGET_RATE = 16000;

export function toBase64(bytes) {
  let out = "";
  for (let i = 0; i < bytes.length; i += 0x8000) out += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(out);
}

// Float samples at the device's rate become 16-bit PCM at 16 kHz inside a WAV file.
export function encodeWav(chunks, inRate) {
  let total = 0;
  for (const c of chunks) total += c.length;
  const mono = new Float32Array(total);
  let at = 0;
  for (const c of chunks) { mono.set(c, at); at += c.length; }
  const ratio = inRate / TARGET_RATE;
  const count = Math.floor(total / ratio);
  const pcm = new Int16Array(count);
  for (let i = 0; i < count; i++) {
    const from = Math.floor(i * ratio), to = Math.min(total, Math.floor((i + 1) * ratio));
    let sum = 0, n = 0;
    for (let j = from; j < to; j++) { sum += mono[j]; n++; }
    const v = Math.max(-1, Math.min(1, n ? sum / n : 0));
    pcm[i] = Math.round(v * 32767);
  }
  const wav = new Uint8Array(44 + pcm.length * 2);
  const view = new DataView(wav.buffer);
  const text = (offset, s) => { for (let i = 0; i < s.length; i++) wav[offset + i] = s.charCodeAt(i); };
  text(0, "RIFF"); view.setUint32(4, 36 + pcm.length * 2, true); text(8, "WAVE");
  text(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, TARGET_RATE, true); view.setUint32(28, TARGET_RATE * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  text(36, "data"); view.setUint32(40, pcm.length * 2, true);
  for (let i = 0; i < pcm.length; i++) view.setInt16(44 + i * 2, pcm[i], true);
  return { wav, seconds: count / TARGET_RATE };
}

// Opens the microphone and records until you stop talking (or tap, or 30 seconds pass).
// Resolves { wav, heard, seconds, reason }: wav is null when no speech was heard.
export async function startRecording(ctx, { onLevel } = {}) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
  if (ctx.state === "suspended") { try { await ctx.resume(); } catch {} }
  const source = ctx.createMediaStreamSource(stream);
  const proc = ctx.createScriptProcessor(4096, 1, 1);
  const chunks = [];
  const started = performance.now();
  let heard = false, lastSpeech = 0, floor = 0, finished = false, discard = false, finishWith;
  const done = new Promise((resolve) => { finishWith = resolve; });

  const end = (reason) => {
    if (finished) return;
    finished = true;
    try { proc.disconnect(); source.disconnect(); } catch {}
    for (const track of stream.getTracks()) track.stop();
    onLevel?.(0);
    if (discard || !heard) { finishWith({ wav: null, heard: false, seconds: 0, reason: discard ? "cancelled" : reason }); return; }
    const { wav, seconds } = encodeWav(chunks, ctx.sampleRate);
    finishWith({ wav, heard: true, seconds, reason });
  };

  proc.onaudioprocess = (e) => {
    if (finished) return;
    const data = e.inputBuffer.getChannelData(0);
    chunks.push(new Float32Array(data));
    let sum = 0;
    for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
    const rms = Math.sqrt(sum / data.length);
    onLevel?.(rms);
    const now = performance.now() - started;
    // Learn the room's background level in the first 0.4 seconds, then call anything clearly above it speech.
    if (now < 400) { floor = Math.max(floor, rms); return; }
    if (rms > Math.max(0.012, Math.min(floor * 2.5, 0.05))) { heard = true; lastSpeech = now; }
    if (heard && now - lastSpeech > 1300) end("silence");
    else if (!heard && now > 7000) end("nothing");
    else if (now > 30000) end("limit");
  };
  source.connect(proc);
  proc.connect(ctx.destination); // Safari only runs the processor when it's connected; it writes silence

  return { done, stop: () => end("tap"), cancel: () => { discard = true; end("cancelled"); } };
}

// For the microphone test: opens the microphone for a moment and reports the loudest level it heard.
export async function measureMic(ctx, ms, onLevel) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  try {
    if (ctx.state === "suspended") { try { await ctx.resume(); } catch {} }
    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 1024;
    source.connect(analyser);
    const buf = new Float32Array(analyser.fftSize);
    let max = 0;
    const until = performance.now() + ms;
    while (performance.now() < until) {
      analyser.getFloatTimeDomainData(buf);
      let sum = 0;
      for (const v of buf) sum += v * v;
      const rms = Math.sqrt(sum / buf.length);
      max = Math.max(max, rms);
      onLevel?.(rms);
      await new Promise((r) => setTimeout(r, 80));
    }
    source.disconnect();
    return { max, tracks: stream.getAudioTracks().map((t) => `${t.label || "microphone"} (${t.readyState})`).join(", ") };
  } finally {
    for (const track of stream.getTracks()) track.stop();
    onLevel?.(0);
  }
}
