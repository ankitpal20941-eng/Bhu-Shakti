import { type ClassValue, clsx } from "clsx";

/**
 * Standard Shadcn UI class name merger utility
 */
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}
