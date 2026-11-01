"""Pausas reales y entonacion medidas sobre el audio (energia y Praat), mas fiables que las marcas de Whisper."""
import wave

import numpy as np

from mkyt_core.paths import INPUT, WORK
from mkyt_core.proc import run

FRAME = 0.02  # s
SR = 16000


class SpeechMap:
    def __init__(self, video_id):
        self.video_id = video_id
        wav = WORK / video_id / "audio.wav"
        if not wav.exists():
            wav.parent.mkdir(parents=True, exist_ok=True)
            run(["ffmpeg", "-y", "-v", "error", "-i", INPUT / f"{video_id}.mp4", "-vn", "-ac", 1, "-ar", SR, wav])
        with wave.open(str(wav), "rb") as w:
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768.0
        n = int(SR * FRAME)
        fr = x[: len(x) // n * n].reshape(-1, n)
        self.db = 20 * np.log10(np.sqrt(np.mean(fr ** 2, axis=1)) + 1e-9)
        self.voiced = self.db > (np.percentile(self.db, 95) - 30)

    def _i(self, t):
        return int(t / FRAME)

    def pause_after(self, t, max_search=1.5, min_pause=0.12):
        """Primera pausa real (>= min_pause) que empieza en [t-0.05, t+max_search].
        Devuelve (inicio_pausa, duración) o None si el habla continúa sin pausa."""
        i = max(self._i(t - 0.05), 0)
        end = min(self._i(t + max_search), len(self.voiced) - 1)
        while i < end:
            if not self.voiced[i]:
                j = i
                while j < len(self.voiced) and not self.voiced[j]:
                    j += 1
                dur = (j - i) * FRAME
                if dur >= min_pause:
                    return i * FRAME, dur
                i = j
            else:
                i += 1
        return None

    def ending(self, t_end):
        """Entonación de la frase que termina en t_end (inicio de la pausa).
        Devuelve {"tipo": "cierra"|"sube"|"plano"|"?", "caida_st": .., "pendiente_st_s": ..}.
          cierra = tono final claramente bajo y descendente (frase terminada)
          sube   = el tono sube al final (viene otra frase)
          plano  = se queda en alto/sostenido (suspensivo, suele continuar)
        Medido con Praat sobre los últimos ~0.7 s con voz antes de la pausa."""
        import numpy as np
        import parselmouth

        if not hasattr(self, "_pitch"):
            wav = WORK / self.video_id / "audio.wav"
            snd = parselmouth.Sound(str(wav))
            self._pitch = snd.to_pitch(time_step=0.01, pitch_floor=70, pitch_ceiling=330)
        p = self._pitch
        times = p.xs()
        f0 = p.selected_array["frequency"]
        voiced = f0 > 0
        # contexto de referencia: mediana del tono del hablante en los 6 s anteriores
        ref_m = (times >= t_end - 6.0) & (times <= t_end) & voiced
        win_m = (times >= t_end - 0.7) & (times <= t_end + 0.05) & voiced
        if ref_m.sum() < 30 or win_m.sum() < 12:
            return {"tipo": "?", "caida_st": None, "pendiente_st_s": None}
        st = lambda hz: 12 * np.log2(hz / 100.0)
        ref_med = float(np.median(st(f0[ref_m])))
        tw, sw = times[win_m], st(f0[win_m])
        slope = float(np.polyfit(tw, sw, 1)[0])                 # st/s sobre la ventana
        tail = float(np.median(sw[-max(len(sw) // 4, 4):]))      # tono del final
        head = float(np.median(sw[: max(len(sw) // 2, 4)]))      # tono de la primera parte de la ventana
        below_ref = tail - ref_med                                 # < 0: por debajo de su tono habitual
        if slope > 3 or tail - head > 1.5:
            tipo = "sube"
        elif below_ref <= -1.5 and slope < -2:
            tipo = "cierra"
        elif below_ref <= -3:
            tipo = "cierra"
        else:
            tipo = "plano"
        return {"tipo": tipo, "caida_st": round(below_ref, 1), "pendiente_st_s": round(slope, 1)}

    def onset_after(self, t, max_search=1.6):
        """Si en t hay silencio, devuelve cuándo empieza el habla de verdad (<= t+max_search); si ya hay habla, None."""
        i = self._i(t)
        if i >= len(self.voiced) or self.voiced[i]:
            return None
        end = min(self._i(t + max_search), len(self.voiced) - 1)
        while i < end:
            if self.voiced[i]:
                return i * FRAME
            i += 1
        return None

    def voiced_at(self, t):
        i = self._i(t)
        return bool(self.voiced[i]) if 0 <= i < len(self.voiced) else False

    def lead_before(self, t, max_lead=0.15):
        """Cuánto se puede retroceder desde t sin entrar en el habla anterior."""
        i = self._i(t) - 1
        n = 0
        while i >= 0 and not self.voiced[i] and n * FRAME < max_lead:
            i -= 1
            n += 1
        return max(n * FRAME - 0.02, 0.0)

    def pauses(self, a, b, min_pause=0.35):
        out, i, end = [], self._i(a), min(self._i(b), len(self.voiced))
        while i < end:
            if not self.voiced[i]:
                j = i
                while j < len(self.voiced) and not self.voiced[j]:
                    j += 1
                if (j - i) * FRAME >= min_pause:
                    out.append((i * FRAME, (j - i) * FRAME))
                i = j
            else:
                i += 1
        return out
