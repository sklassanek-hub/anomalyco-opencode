interface Option {
  value: string;
  label: string;
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: (Option | string)[];
  placeholder?: string;
  error?: string;
  errorId?: string;
}

export default function Select({ label, options, placeholder, error, errorId, className = '', ...rest }: SelectProps) {
  const hasError = !!error;
  const ariaDesc = hasError && errorId ? errorId : undefined;
  return (
    <label className={`field ${className}`}>
      {label && <span className="field-label">{label}</span>}
      <select
        className={`select${hasError ? ' select-error' : ''}`}
        aria-invalid={hasError ? 'true' : undefined}
        aria-describedby={ariaDesc}
        {...rest}
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => {
          const opt = typeof o === 'string' ? { value: o, label: o } : o;
          return (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          );
        })}
      </select>
      {hasError && (
        <span id={errorId || 'select-error'} role="alert" className="field-error" aria-live="assertive">
          {error}
        </span>
      )}
    </label>
  );
}