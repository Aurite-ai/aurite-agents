import React, { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FolderOpen, FileCode } from 'lucide-react';

interface FilePickerProps {
  value: string;                    // Current module path
  onChange: (modulePath: string) => void;
  placeholder?: string;
  defaultDirectory?: string;        // Default to "/custom_workflows"
  label?: string;
}

// Utility function to convert file path to Python module path
const convertFilePathToModulePath = (filePath: string): string => {
  // Remove file extension and convert slashes to dots
  return filePath
    .replace(/\.py$/, '')           // Remove .py extension
    .replace(/^\/+/, '')           // Remove leading slashes
    .replace(/\/+/g, '.')          // Convert slashes to dots
    .replace(/^\.+/, '');          // Remove leading dots
};

// Utility function to convert module path back to file path (for display)
const convertModulePathToFilePath = (modulePath: string): string => {
  if (!modulePath) return '';
  return modulePath.replace(/\./g, '/') + '.py';
};

export const FilePicker: React.FC<FilePickerProps> = ({ 
  value, 
  onChange, 
  placeholder = "Select Python file...",
  defaultDirectory = "custom_workflows",
  label = "Module Path"
}) => {
  const [selectedFilePath, setSelectedFilePath] = useState<string>(
    value ? convertModulePathToFilePath(value) : ''
  );
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // For demo purposes, we'll simulate a path structure
      const simulatedPath = `${defaultDirectory}/${file.name}`;
      
      setSelectedFilePath(simulatedPath);
      const modulePath = convertFilePathToModulePath(simulatedPath);
      onChange(modulePath);
    }
  };

  const handleManualPathChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const filePath = event.target.value;
    setSelectedFilePath(filePath);
    
    if (filePath.endsWith('.py')) {
      const modulePath = convertFilePathToModulePath(filePath);
      onChange(modulePath);
    }
  };

  const openFileBrowser = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="space-y-2">
      <Label htmlFor="file-picker" className="text-sm font-medium text-foreground">
        {label} *
      </Label>
      
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".py"
        onChange={handleFileSelect}
        className="hidden"
        id="file-picker-input"
      />
      
      {/* File path input with browse button */}
      <div className="flex gap-2">
        <Input
          id="file-picker"
          placeholder={placeholder}
          value={selectedFilePath}
          onChange={handleManualPathChange}
          className="text-base flex-1"
        />
        <Button
          type="button"
          variant="outline"
          onClick={openFileBrowser}
          className="flex items-center gap-2 px-3"
        >
          <FolderOpen className="h-4 w-4" />
          Browse
        </Button>
      </div>
      
      {/* Module path display */}
      {value && (
        <div className="flex items-center gap-2 p-2 bg-muted/20 rounded-md border border-border">
          <FileCode className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">
            Module: <code className="text-foreground font-mono">{value}</code>
          </span>
        </div>
      )}
      
      <p className="text-xs text-muted-foreground">
        Select a Python file or enter the file path manually. The path will be automatically converted to a Python module path.
      </p>
    </div>
  );
};

export default FilePicker;
