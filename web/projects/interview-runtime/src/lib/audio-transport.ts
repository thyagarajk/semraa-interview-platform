import { Observable } from 'rxjs';

/** 16 kHz mono PCM frame with a sequence number; the server rejects duplicates and detects gaps. */
export interface AudioFrame {
  readonly sequence: number;
  readonly pcm: Int16Array;
}

export type ServerEvent =
  | { readonly type: 'caption'; readonly text: string; readonly final: boolean }
  | {
      readonly type: 'turn';
      readonly turnId: string;
      readonly state: 'speaking' | 'listening' | 'thinking';
    }
  | { readonly type: 'timer'; readonly remainingSeconds: number }
  | { readonly type: 'ended'; readonly reason: string };

/**
 * Transport behind an interface (architecture doc 5.6): WSS first, WebRTC later without touching the UI.
 * The socket opens with a one-time session ticket, never a bearer token in the URL.
 */
export interface AudioTransport {
  connect(sessionTicket: string): Promise<void>;
  send(frame: AudioFrame): void;
  readonly events$: Observable<ServerEvent>;
  close(): void;
}
