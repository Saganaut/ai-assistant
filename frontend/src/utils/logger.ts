const isDev = import.meta.env.DEV;

export const log = (...args: unknown[]) => {
  if (isDev) console.log(...args);
};

export const warn = (...args: unknown[]) => {
  if (isDev) console.warn(...args);
};

export const error = (...args: unknown[]) => {
  if (isDev) console.error(...args);
};
