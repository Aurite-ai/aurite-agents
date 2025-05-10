import React from 'react';

interface StructuredResponseViewProps {
  data: Record<string, any>;
}

const renderValue = (value: any, keyPrefix: string): JSX.Element | null => {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return <span className="text-dracula-purple">{String(value)}</span>;
  }

  if (Array.isArray(value)) {
    return (
      <ul className="list-disc list-inside ml-4">
        {value.map((item, index) => (
          <li key={`${keyPrefix}-${index}`} className="text-dracula-foreground">
            {renderValue(item, `${keyPrefix}-${index}`)}
          </li>
        ))}
      </ul>
    );
  }

  if (typeof value === 'object' && value !== null) {
    return (
      <div className="ml-4 pl-4 border-l border-dracula-comment">
        {Object.entries(value).map(([key, val]) => (
          <div key={`${keyPrefix}-${key}`} className="mb-1">
            <strong className="text-dracula-cyan">{key}: </strong>
            {renderValue(val, `${keyPrefix}-${key}`)}
          </div>
        ))}
      </div>
    );
  }
  return <span className="text-dracula-comment">null</span>; // Or some other placeholder for null/undefined
};

const StructuredResponseView: React.FC<StructuredResponseViewProps> = ({ data }) => {
  if (!data || typeof data !== 'object' || Object.keys(data).length === 0) {
    return <div className="p-2 text-dracula-comment italic">No structured data to display.</div>;
  }

  return (
    <div className="p-3 bg-dracula-current-line rounded-md shadow text-sm text-dracula-foreground">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="mb-2">
          <strong className="text-dracula-green">{key}: </strong>
          {renderValue(value, key)}
        </div>
      ))}
    </div>
  );
};

export default StructuredResponseView;
