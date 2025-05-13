import React, { useState, useEffect } from 'react';

interface SelectableItem {
  id: string;
  displayName: string;
}

interface MultiSelectModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  items: SelectableItem[];
  selectedIds: string[];
  onConfirmSelection: (newSelectedIds: string[]) => void;
}

const MultiSelectModal: React.FC<MultiSelectModalProps> = ({
  isOpen,
  onClose,
  title,
  items,
  selectedIds,
  onConfirmSelection,
}) => {
  const [currentSelections, setCurrentSelections] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (isOpen) {
      setCurrentSelections(new Set(selectedIds));
    }
  }, [isOpen, selectedIds]);

  if (!isOpen) {
    return null;
  }

  const handleToggleSelection = (itemId: string) => {
    setCurrentSelections(prev => {
      const newSelections = new Set(prev);
      if (newSelections.has(itemId)) {
        newSelections.delete(itemId);
      } else {
        newSelections.add(itemId);
      }
      return newSelections;
    });
  };

  const handleConfirm = () => {
    onConfirmSelection(Array.from(currentSelections));
    onClose();
  };

  const handleCancel = () => {
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-dracula-background bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-dracula-current-line rounded-lg shadow-xl p-6 w-full max-w-md max-h-[80vh] flex flex-col">
        <h2 className="text-xl font-semibold text-dracula-pink mb-4">{title}</h2>

        <div className="overflow-y-auto mb-4 pr-2 space-y-2 flex-grow">
          {items.length === 0 && <p className="text-dracula-comment">No items available.</p>}
          {items.map(item => (
            <div key={item.id} className="flex items-center p-2 rounded-md hover:bg-dracula-selection transition-colors">
              <input
                type="checkbox"
                id={`msm-item-${item.id}`}
                checked={currentSelections.has(item.id)}
                onChange={() => handleToggleSelection(item.id)}
                className="h-4 w-4 text-dracula-pink bg-dracula-background border-dracula-comment rounded focus:ring-dracula-pink focus:ring-offset-0"
              />
              <label htmlFor={`msm-item-${item.id}`} className="ml-3 block text-sm font-medium text-dracula-foreground select-none">
                {item.displayName}
              </label>
            </div>
          ))}
        </div>

        <div className="flex justify-end space-x-3 pt-4 border-t border-dracula-comment">
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-sm font-medium text-dracula-foreground bg-dracula-selection hover:bg-opacity-70 rounded-md focus:outline-none focus:ring-2 focus:ring-dracula-pink"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className="px-4 py-2 text-sm font-medium text-dracula-background bg-dracula-green hover:bg-opacity-90 rounded-md focus:outline-none focus:ring-2 focus:ring-dracula-pink"
          >
            Confirm Selections
          </button>
        </div>
      </div>
    </div>
  );
};

export default MultiSelectModal;
