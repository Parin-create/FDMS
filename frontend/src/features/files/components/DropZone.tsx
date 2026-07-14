import { useRef, useState, type DragEvent, type KeyboardEvent } from 'react';

import { ALLOWED_EXTENSIONS, MAX_FILE_SIZE_LABEL } from '@/features/files/constants';

interface DropZoneProps {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
}

/** Drag-and-drop area plus click-to-browse (single file). */
export function DropZone({ onFileSelected, disabled = false }: DropZoneProps): JSX.Element {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  const pick = (files: FileList | null): void => {
    const file = files?.[0];
    if (file) {
      onFileSelected(file);
    }
  };

  const openPicker = (): void => {
    if (!disabled) {
      inputRef.current?.click();
    }
  };

  const onDrop = (event: DragEvent<HTMLDivElement>): void => {
    event.preventDefault();
    setDragActive(false);
    if (!disabled) {
      pick(event.dataTransfer.files);
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openPicker();
    }
  };

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      onClick={openPicker}
      onKeyDown={onKeyDown}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragActive(true);
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={onDrop}
      className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
        disabled
          ? 'cursor-not-allowed border-gray-200 bg-gray-50'
          : dragActive
            ? 'cursor-pointer border-brand-500 bg-brand-50'
            : 'cursor-pointer border-gray-300 bg-white hover:border-brand-400 hover:bg-gray-50'
      }`}
    >
      <svg
        className={`h-10 w-10 ${dragActive ? 'text-brand-600' : 'text-gray-400'}`}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        aria-hidden="true"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V6m0 0-3.5 3.5M12 6l3.5 3.5" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 16.5v1.75A2.25 2.25 0 0 0 6.75 20.5h10.5a2.25 2.25 0 0 0 2.25-2.25V16.5" />
      </svg>
      <p className="mt-3 text-sm font-medium text-gray-800">
        Drag &amp; drop a file here, or <span className="text-brand-600">browse</span>
      </p>
      <p className="mt-1 text-xs text-gray-500">
        Up to {MAX_FILE_SIZE_LABEL}. {ALLOWED_EXTENSIONS.join(', ')}
      </p>

      <input
        ref={inputRef}
        type="file"
        className="hidden"
        disabled={disabled}
        onChange={(e) => {
          pick(e.target.files);
          e.target.value = '';
        }}
      />
    </div>
  );
}
