import { useEffect, useRef, useState } from "react";
import Modal from "./Modal";

interface Props {
  onDetect: (code: string) => void;
  onClose: () => void;
}

/** Camera-based barcode scanning (spec section 4: "camera-based
 * barcode scanning as an alternative to a hardware scanner").
 *
 * Uses the browser's native BarcodeDetector API rather than pulling in
 * a JS decoding library — as of writing this ships in Chrome, Edge,
 * and Android WebView (the large majority of real-world POS
 * hardware: Android tablets and phones), which covers the actual
 * target device for a business running this at the counter. Where
 * it's unavailable (Safari, Firefox), this degrades to a clear
 * message rather than a silent failure — the existing physical-
 * scanner and type-to-search paths in POS still work regardless, so
 * nobody is ever blocked from selling because of browser support.
 */
export default function CameraBarcodeScanner({ onDetect, onClose }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [supported, setSupported] = useState(true);
  const [lastCode, setLastCode] = useState<string | null>(null);

  useEffect(() => {
    if (!("BarcodeDetector" in window)) {
      setSupported(false);
      return;
    }

    let cancelled = false;
    // @ts-expect-error — BarcodeDetector isn't in TS's default lib yet.
    const detector = new window.BarcodeDetector({
      formats: ["ean_13", "ean_8", "upc_a", "upc_e", "code_128", "code_39", "qr_code"],
    });

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" } })
      .then((stream) => {
        if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return; }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }

        const scanFrame = async () => {
          if (cancelled || !videoRef.current) return;
          try {
            const codes = await detector.detect(videoRef.current);
            if (codes.length > 0) {
              const value = codes[0].rawValue;
              setLastCode(value);
              onDetect(value);
              return; // stop scanning once we've found one
            }
          } catch {
            // A single failed frame isn't worth surfacing — camera
            // decoding briefly fails on out-of-focus frames constantly
            // under normal use; only a total permission/device
            // failure (caught below) is worth telling the user about.
          }
          rafRef.current = requestAnimationFrame(scanFrame);
        };
        rafRef.current = requestAnimationFrame(scanFrame);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          err?.name === "NotAllowedError"
            ? "Camera access was denied. Allow camera access in your browser settings, or use the search box instead."
            : "Couldn't access the camera. You can still type the barcode or use a physical scanner."
        );
      });

    return () => {
      cancelled = true;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [onDetect]);

  return (
    <Modal title="Scan barcode" onClose={onClose}>
      {!supported ? (
        <p style={{ fontSize: 15.5, color: "var(--ink-600)" }}>
          Camera scanning isn't supported in this browser. It works in Chrome, Edge, and most Android
          devices — or you can keep using a physical barcode scanner or type the code directly.
        </p>
      ) : error ? (
        <p className="inline-error">{error}</p>
      ) : (
        <>
          <div style={{ position: "relative", borderRadius: 10, overflow: "hidden", background: "#000" }}>
            <video ref={videoRef} muted playsInline style={{ width: "100%", display: "block" }} />
            <div
              style={{
                position: "absolute", top: "35%", left: "10%", right: "10%", height: "30%",
                border: "2px solid var(--gold-500, #d4af37)", borderRadius: 8, pointerEvents: "none",
              }}
            />
          </div>
          <p style={{ fontSize: 14.5, color: "var(--ink-300)", marginTop: 10, textAlign: "center" }}>
            {lastCode ? `Found: ${lastCode}` : "Point the camera at a barcode."}
          </p>
        </>
      )}
    </Modal>
  );
}
