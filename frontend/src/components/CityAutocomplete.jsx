import { useEffect, useRef, useState } from "react";
import { searchCities } from "../api";

export default function CityAutocomplete({ id, label, value, onChange, onText, placeholder }) {
  const [text, setText] = useState(value?.label || "");
  const [options, setOptions] = useState([]);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(-1);
  const boxRef = useRef(null);
  const timer = useRef(null);

  // Keep the visible text in sync when the value is set from outside (e.g. swap).
  useEffect(() => {
    setText(value?.label || "");
  }, [value]);

  useEffect(() => {
    function onClickOutside(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  function handleInput(e) {
    const q = e.target.value;
    setText(q);
    onChange(null); // typing invalidates a previously chosen city
    onText?.(q);
    clearTimeout(timer.current);
    if (q.trim().length < 2) {
      setOptions([]);
      setOpen(false);
      return;
    }
    timer.current = setTimeout(async () => {
      const results = await searchCities(q);
      setOptions(results);
      setOpen(results.length > 0);
      setHighlight(-1);
    }, 180);
  }

  function choose(opt) {
    onChange(opt);
    setText(opt.label);
    setOpen(false);
    setOptions([]);
  }

  function onKeyDown(e) {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((h) => Math.min(h + 1, options.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === "Enter" && highlight >= 0) {
      e.preventDefault();
      choose(options[highlight]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div className="ac" ref={boxRef}>
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        autoComplete="off"
        value={text}
        onChange={handleInput}
        onKeyDown={onKeyDown}
        onFocus={() => options.length && setOpen(true)}
        placeholder={placeholder}
      />
      {open && (
        <ul className="ac-menu" role="listbox">
          {options.map((opt, i) => (
            <li
              key={opt.label}
              role="option"
              aria-selected={i === highlight}
              className={i === highlight ? "active" : ""}
              onMouseEnter={() => setHighlight(i)}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(opt);
              }}
            >
              <span className="ac-city">{opt.city}</span>
              <span className="ac-state">{opt.state}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
