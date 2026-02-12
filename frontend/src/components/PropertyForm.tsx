import { useState, useCallback } from 'react';
import type { GenerateRequest } from '@/services/api';

// ---------------------------------------------------------------------------
// US States
// ---------------------------------------------------------------------------

const US_STATES = [
  { value: 'AL', label: 'Alabama' },
  { value: 'AK', label: 'Alaska' },
  { value: 'AZ', label: 'Arizona' },
  { value: 'AR', label: 'Arkansas' },
  { value: 'CA', label: 'California' },
  { value: 'CO', label: 'Colorado' },
  { value: 'CT', label: 'Connecticut' },
  { value: 'DE', label: 'Delaware' },
  { value: 'FL', label: 'Florida' },
  { value: 'GA', label: 'Georgia' },
  { value: 'HI', label: 'Hawaii' },
  { value: 'ID', label: 'Idaho' },
  { value: 'IL', label: 'Illinois' },
  { value: 'IN', label: 'Indiana' },
  { value: 'IA', label: 'Iowa' },
  { value: 'KS', label: 'Kansas' },
  { value: 'KY', label: 'Kentucky' },
  { value: 'LA', label: 'Louisiana' },
  { value: 'ME', label: 'Maine' },
  { value: 'MD', label: 'Maryland' },
  { value: 'MA', label: 'Massachusetts' },
  { value: 'MI', label: 'Michigan' },
  { value: 'MN', label: 'Minnesota' },
  { value: 'MS', label: 'Mississippi' },
  { value: 'MO', label: 'Missouri' },
  { value: 'MT', label: 'Montana' },
  { value: 'NE', label: 'Nebraska' },
  { value: 'NV', label: 'Nevada' },
  { value: 'NH', label: 'New Hampshire' },
  { value: 'NJ', label: 'New Jersey' },
  { value: 'NM', label: 'New Mexico' },
  { value: 'NY', label: 'New York' },
  { value: 'NC', label: 'North Carolina' },
  { value: 'ND', label: 'North Dakota' },
  { value: 'OH', label: 'Ohio' },
  { value: 'OK', label: 'Oklahoma' },
  { value: 'OR', label: 'Oregon' },
  { value: 'PA', label: 'Pennsylvania' },
  { value: 'RI', label: 'Rhode Island' },
  { value: 'SC', label: 'South Carolina' },
  { value: 'SD', label: 'South Dakota' },
  { value: 'TN', label: 'Tennessee' },
  { value: 'TX', label: 'Texas' },
  { value: 'UT', label: 'Utah' },
  { value: 'VT', label: 'Vermont' },
  { value: 'VA', label: 'Virginia' },
  { value: 'WA', label: 'Washington' },
  { value: 'WV', label: 'West Virginia' },
  { value: 'WI', label: 'Wisconsin' },
  { value: 'WY', label: 'Wyoming' },
] as const;

const PROPERTY_TYPES = [
  { value: 'garden-style', label: 'Garden-Style' },
  { value: 'mid-rise', label: 'Mid-Rise' },
  { value: 'high-rise', label: 'High-Rise' },
] as const;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Props {
  onSubmit: (data: GenerateRequest) => Promise<void>;
  onLucky: () => Promise<void>;
}

interface FormData {
  property_name: string;
  address: string;
  city: string;
  state: string;
  units: string;
  year_built: string;
  property_type: string;
}

type FormErrors = Partial<Record<keyof FormData, string>>;

const INITIAL_FORM: FormData = {
  property_name: '',
  address: '',
  city: '',
  state: '',
  units: '',
  year_built: '',
  property_type: '',
};

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

function validate(form: FormData): FormErrors {
  const errors: FormErrors = {};

  if (!form.address.trim()) {
    errors.address = 'Address is required.';
  }

  if (!form.city.trim()) {
    errors.city = 'City is required.';
  }

  if (!form.state) {
    errors.state = 'State is required.';
  }

  const units = Number(form.units);
  if (!form.units || isNaN(units)) {
    errors.units = 'Number of units is required.';
  } else if (units < 10 || units > 500) {
    errors.units = 'Units must be between 10 and 500.';
  } else if (!Number.isInteger(units)) {
    errors.units = 'Units must be a whole number.';
  }

  const year = Number(form.year_built);
  if (!form.year_built || isNaN(year)) {
    errors.year_built = 'Year built is required.';
  } else if (year < 1950 || year > 2026) {
    errors.year_built = 'Year must be between 1950 and 2026.';
  } else if (!Number.isInteger(year)) {
    errors.year_built = 'Year must be a whole number.';
  }

  if (!form.property_type) {
    errors.property_type = 'Property type is required.';
  }

  return errors;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PropertyForm({ onSubmit, onLucky }: Props) {
  const [form, setForm] = useState<FormData>(INITIAL_FORM);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [luckySubmitting, setLuckySubmitting] = useState(false);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      const { name, value } = e.target;
      setForm((prev) => ({ ...prev, [name]: value }));
      // Clear field error on change
      setErrors((prev) => {
        if (!prev[name as keyof FormData]) return prev;
        const next = { ...prev };
        delete next[name as keyof FormData];
        return next;
      });
    },
    [],
  );

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      const validationErrors = validate(form);
      if (Object.keys(validationErrors).length > 0) {
        setErrors(validationErrors);
        return;
      }

      setSubmitting(true);
      try {
        await onSubmit({
          property_name: form.property_name.trim() || undefined,
          address: form.address.trim(),
          city: form.city.trim(),
          state: form.state,
          units: Number(form.units),
          year_built: Number(form.year_built),
          property_type: form.property_type as GenerateRequest['property_type'],
        });
      } finally {
        setSubmitting(false);
      }
    },
    [form, onSubmit],
  );

  // Helper to build className for inputs
  const inputClass = (field: keyof FormData) =>
    `input-field ${errors[field] ? 'input-error' : ''}`;

  const handleLucky = useCallback(async () => {
    setLuckySubmitting(true);
    try {
      await onLucky();
    } finally {
      setLuckySubmitting(false);
    }
  }, [onLucky]);

  return (
    <div className="mx-auto max-w-2xl">
      {/* Intro */}
      <div className="mb-8 text-center">
        <h2 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
          Property Details
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          Enter multifamily details manually or use I&apos;m Feeling Lucky to
          auto-generate believable starter inputs with Haiku.
        </p>
      </div>

      {/* Card */}
      <form onSubmit={handleSubmit} noValidate className="card space-y-6">
        {/* Property Name */}
        <div>
          <label htmlFor="property_name" className="label">
            Property Name (optional)
          </label>
          <input
            id="property_name"
            name="property_name"
            type="text"
            placeholder="Smaug Court Apartments"
            value={form.property_name}
            onChange={handleChange}
            className={inputClass('property_name')}
          />
        </div>

        {/* Address */}
        <div>
          <label htmlFor="address" className="label">
            Property Address
          </label>
          <input
            id="address"
            name="address"
            type="text"
            placeholder="123 Main Street"
            value={form.address}
            onChange={handleChange}
            className={inputClass('address')}
          />
          {errors.address && (
            <p className="mt-1 text-xs text-red-500">{errors.address}</p>
          )}
        </div>

        {/* City + State */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="city" className="label">
              City
            </label>
            <input
              id="city"
              name="city"
              type="text"
              placeholder="New York"
              value={form.city}
              onChange={handleChange}
              className={inputClass('city')}
            />
            {errors.city && (
              <p className="mt-1 text-xs text-red-500">{errors.city}</p>
            )}
          </div>

          <div>
            <label htmlFor="state" className="label">
              State
            </label>
            <select
              id="state"
              name="state"
              value={form.state}
              onChange={handleChange}
              className={inputClass('state')}
            >
              <option value="">Select a state</option>
              {US_STATES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
            {errors.state && (
              <p className="mt-1 text-xs text-red-500">{errors.state}</p>
            )}
          </div>
        </div>

        {/* Units + Year Built */}
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="units" className="label">
              Number of Units
            </label>
            <input
              id="units"
              name="units"
              type="number"
              min={10}
              max={500}
              step={1}
              placeholder="120"
              value={form.units}
              onChange={handleChange}
              className={inputClass('units')}
            />
            {errors.units && (
              <p className="mt-1 text-xs text-red-500">{errors.units}</p>
            )}
          </div>

          <div>
            <label htmlFor="year_built" className="label">
              Year Built
            </label>
            <input
              id="year_built"
              name="year_built"
              type="number"
              min={1950}
              max={2026}
              step={1}
              placeholder="2005"
              value={form.year_built}
              onChange={handleChange}
              className={inputClass('year_built')}
            />
            {errors.year_built && (
              <p className="mt-1 text-xs text-red-500">{errors.year_built}</p>
            )}
          </div>
        </div>

        {/* Property Type */}
        <div>
          <label htmlFor="property_type" className="label">
            Property Type
          </label>
          <select
            id="property_type"
            name="property_type"
            value={form.property_type}
            onChange={handleChange}
            className={inputClass('property_type')}
          >
            <option value="">Select a property type</option>
            {PROPERTY_TYPES.map((pt) => (
              <option key={pt.value} value={pt.value}>
                {pt.label}
              </option>
            ))}
          </select>
          {errors.property_type && (
            <p className="mt-1 text-xs text-red-500">{errors.property_type}</p>
          )}
        </div>

        {/* Divider */}
        <hr className="border-slate-200" />

        {/* Submit */}
        <div className="flex items-center justify-end gap-3">
          <button
            type="button"
            disabled={submitting || luckySubmitting}
            onClick={handleLucky}
            className="btn-secondary min-w-[180px]"
          >
            {luckySubmitting ? (
              <>
                <Spinner />
                Summoning Smaug...
              </>
            ) : (
              <>I&apos;m Feeling Lucky</>
            )}
          </button>
          <button
            type="submit"
            disabled={submitting || luckySubmitting}
            className="btn-primary min-w-[180px]"
          >
            {submitting ? (
              <>
                <Spinner />
                Submitting...
              </>
            ) : (
              <>
                <svg
                  className="h-4 w-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
                  />
                </svg>
                Generate Appraisal
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tiny spinner
// ---------------------------------------------------------------------------

function Spinner() {
  return (
    <svg
      className="h-4 w-4 animate-spin"
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
      />
    </svg>
  );
}
