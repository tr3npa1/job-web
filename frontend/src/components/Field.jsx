import React from "react";
export default function Field({
  label,
  name,
  type = "text",
  options,
  required = true,
  ...props
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {options ? (
        <select name={name} required={required} {...props}>
          {options.map(([value, text]) => (
            <option key={value} value={value}>
              {text}
            </option>
          ))}
        </select>
      ) : (
        <input
          name={name}
          type={type}
          required={required}
          maxLength={type === "password" ? 256 : 45}
          {...props}
        />
      )}
    </label>
  );
}
