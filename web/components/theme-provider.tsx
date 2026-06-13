"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";

/**
 * Wraps next-themes. It toggles a `class` ("dark") on <html>, which flips the CSS
 * variables defined in globals.css (:root = light, .dark = dark). Must be a client
 * component because it reads/writes localStorage and the DOM.
 */
export function ThemeProvider({ children, ...props }: React.ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
