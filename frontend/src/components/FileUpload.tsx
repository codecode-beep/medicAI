import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, Image, X, Loader2 } from 'lucide-react';

interface FileUploadProps {
  onUpload: (file: File) => void;
  isLoading?: boolean;
  accept?: Record<string, string[]>;
}

export default function FileUpload({ onUpload, isLoading, accept }: FileUploadProps) {
  const [preview, setPreview] = useState<{ file: File; url: string } | null>(null);

  const onDrop = useCallback((accepted: File[]) => {
    const file = accepted[0];
    if (!file) return;
    const url = file.type.startsWith('image/') ? URL.createObjectURL(file) : '';
    setPreview({ file, url });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: accept || {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.webp', '.tiff'],
    },
    maxFiles: 1,
    disabled: isLoading,
  });

  const handleSubmit = () => {
    if (preview) onUpload(preview.file);
  };

  const clear = () => {
    if (preview?.url) URL.revokeObjectURL(preview.url);
    setPreview(null);
  };

  return (
    <div className="space-y-4">
      {!preview ? (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
            isDragActive ? 'border-primary-500 bg-primary-50' : 'border-slate-300 hover:border-primary-400'
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="w-10 h-10 mx-auto text-slate-400 mb-3" />
          <p className="text-slate-600 font-medium">
            {isDragActive ? 'Drop file here' : 'Drag & drop medical files here'}
          </p>
          <p className="text-sm text-slate-400 mt-1">PDFs, prescriptions, X-rays, MRIs, CT scans</p>
        </div>
      ) : (
        <div className="border rounded-xl p-4 bg-white">
          <div className="flex items-start gap-4">
            {preview.url ? (
              <img src={preview.url} alt="Preview" className="w-24 h-24 object-cover rounded-lg" />
            ) : (
              <div className="w-24 h-24 bg-red-50 rounded-lg flex items-center justify-center">
                <FileText className="w-10 h-10 text-red-400" />
              </div>
            )}
            <div className="flex-1">
              <p className="font-medium">{preview.file.name}</p>
              <p className="text-sm text-slate-500">
                {(preview.file.size / 1024).toFixed(1)} KB ·{' '}
                {preview.file.type.startsWith('image/') ? 'Image' : 'PDF'}
              </p>
            </div>
            <button onClick={clear} className="p-1 hover:bg-slate-100 rounded">
              <X className="w-5 h-5 text-slate-400" />
            </button>
          </div>
          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className="mt-4 w-full bg-primary-600 text-white py-2.5 rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Image className="w-4 h-4" />}
            {isLoading ? 'Analyzing...' : 'Analyze with AI'}
          </button>
        </div>
      )}
    </div>
  );
}

