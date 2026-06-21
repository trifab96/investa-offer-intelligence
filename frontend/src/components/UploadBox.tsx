import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadOffer } from "../api";

export default function UploadBox() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (files: FileList) => uploadOffer(files),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["offers"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  function handleFiles(files: FileList | null) {
    if (files && files.length > 0) mutation.mutate(files);
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={`cursor-pointer rounded-lg border-2 border-dashed px-8 py-10 text-center transition ${
        dragging
          ? "border-investa-500 bg-investa-500/5"
          : "border-slate-300 bg-white hover:border-investa-500 hover:bg-slate-50"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".msg,.eml,.pdf,.png,.jpg,.jpeg,.txt"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <p className="eyebrow mb-2">Angebot einreichen</p>
      <p className="font-display text-lg text-investa-800">
        E-Mail (.msg / .eml) und Anhänge hierher ziehen
      </p>
      <p className="mt-1 text-sm text-slate-500">
        oder klicken, um Dateien auszuwählen · PDF, Bilder und Text werden
        verarbeitet
      </p>
      {mutation.isPending && (
        <p className="mt-4 text-sm font-medium text-investa-600">
          Wird hochgeladen …
        </p>
      )}
      {mutation.isError && (
        <p className="mt-4 text-sm text-rose-600">
          Fehler beim Upload: {(mutation.error as Error).message}
        </p>
      )}
      {mutation.isSuccess && (
        <p className="mt-4 text-sm text-emerald-600">
          Angebot empfangen – die Analyse läuft.
        </p>
      )}
    </div>
  );
}
