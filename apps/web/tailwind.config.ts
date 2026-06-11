import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: { "2xl": "1280px" },
    },
    extend: {
      fontFamily: {
        sans: ["var(--font-serif)", "ui-serif", "Georgia", "serif"],
        display: [
          "var(--font-display)",
          "Cinzel",
          "Trajan Pro",
          "Times New Roman",
          "serif",
        ],
        serif: [
          "var(--font-serif)",
          "Cormorant Garamond",
          "EB Garamond",
          "Georgia",
          "serif",
        ],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        // Re-tuned for an editorial layout. 18 / 30 body, 8xl-10xl heroes.
        "eyebrow": ["0.7rem", { lineHeight: "1", letterSpacing: "0.32em" }],
        "9xl": ["clamp(4rem, 9vw, 8.5rem)", { lineHeight: "0.95", letterSpacing: "-0.02em" }],
        "10xl": ["clamp(5rem, 12vw, 11rem)", { lineHeight: "0.92", letterSpacing: "-0.025em" }],
      },
      colors: {
        // shadcn semantic tokens (mapped via globals.css CSS vars)
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Chart semantic tokens
        chart: {
          "1": "hsl(var(--chart-1))",
          "2": "hsl(var(--chart-2))",
          "3": "hsl(var(--chart-3))",
          "4": "hsl(var(--chart-4))",
          "5": "hsl(var(--chart-5))",
        },
        // Athean palette retained for legacy class names
        pantheon: {
          ink: "#0a0e16",
          parchment: "#f7f3e9",
          gold: "#c8a85a",
          marble: "#cdd2da",
        },
      },
      borderRadius: {
        lg: "0",
        md: "0",
        sm: "0",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "shimmer-slide": {
          to: { transform: "translate(calc(100cqw - 100%), 0)" },
        },
        "spin-around": {
          "0%":       { transform: "translateZ(0) rotate(0)" },
          "15%, 35%": { transform: "translateZ(0) rotate(90deg)" },
          "65%, 85%": { transform: "translateZ(0) rotate(270deg)" },
          "100%":     { transform: "translateZ(0) rotate(360deg)" },
        },
        "shine": {
          "0%":   { backgroundPosition: "0% 0%" },
          "50%":  { backgroundPosition: "100% 100%" },
          "100%": { backgroundPosition: "0% 0%" },
        },
        "marquee": {
          from: { transform: "translateX(0)" },
          to:   { transform: "translateX(calc(-100% - var(--gap)))" },
        },
        "marquee-vertical": {
          from: { transform: "translateY(0)" },
          to:   { transform: "translateY(calc(-100% - var(--gap)))" },
        },
      },
      animation: {
        "accordion-down":    "accordion-down 0.2s ease-out",
        "accordion-up":      "accordion-up 0.2s ease-out",
        "shimmer-slide":     "shimmer-slide var(--speed, 3s) ease-in-out infinite alternate",
        "spin-around":       "spin-around calc(var(--speed, 3s) * 2) infinite linear",
        "shine":             "shine var(--duration, 2s) infinite linear",
        "marquee":           "marquee var(--duration, 40s) infinite linear",
        "marquee-vertical":  "marquee-vertical var(--duration, 40s) linear infinite",
      },
    },
  },
  plugins: [animate],
};

export default config;
