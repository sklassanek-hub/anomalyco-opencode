interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  errorId?: string;
}

export default function Input({ label, hint, error, errorId, className = '', ...rest }: InputProps) {
  const hasError = !!error;
  const ariaDesc = hasError && errorId ? errorId : undefined;
  return (
    <label className={`field ${className}`}>
      {label && <span className="field-label">{label}</span>}
      <input
        className={`input${hasError ? ' input-error' : ''}`}
        aria-invalid={hasError ? 'true' : undefined}
        aria-describedby={ariaDesc}
        {...rest}
      />
      {hint && <span className="field-hint">{hint}</span>}
      {hasError && (
        <span id={errorId || 'input-error'} role="alert" className="field-error" aria-live="assertive">
          {error}
        </span>
      )}
    </label>
  );
}