import colors from "colors";

// Configure colors to be safe for terminals
colors.enable();

export enum LogLevel {
  DEBUG = "DEBUG",
  INFO = "INFO",
  WARN = "WARN",
  ERROR = "ERROR",
  SUCCESS = "SUCCESS",
}

interface LogOptions {
  timestamp?: boolean;
  prefix?: string;
  level?: LogLevel;
}

class Logger {
  private static getTimestamp(): string {
    return new Date().toISOString();
  }

  private static formatMessage(
    message: string,
    options: LogOptions = {}
  ): string {
    const parts: string[] = [];

    if (options.timestamp) {
      parts.push(`[${this.getTimestamp()}]`);
    }

    if (options.prefix) {
      parts.push(`[${options.prefix}]`);
    }

    if (options.level) {
      parts.push(`[${options.level}]`);
    }

    parts.push(message);
    return parts.join(" ");
  }

  static debug(message: string, options: LogOptions = {}): void {
    const formattedMessage = this.formatMessage(message, {
      ...options,
      level: LogLevel.DEBUG,
    });
    console.log(colors.gray(formattedMessage));
  }

  static info(message: string, options: LogOptions = {}): void {
    const formattedMessage = this.formatMessage(message, {
      ...options,
      level: LogLevel.INFO,
    });
    console.log(colors.blue(formattedMessage));
  }

  static warn(message: string, options: LogOptions = {}): void {
    const formattedMessage = this.formatMessage(message, {
      ...options,
      level: LogLevel.WARN,
    });
    console.log(colors.yellow(formattedMessage));
  }

  static error(message: string, options: LogOptions = {}): void {
    const formattedMessage = this.formatMessage(message, {
      ...options,
      level: LogLevel.ERROR,
    });
    console.log(colors.red(formattedMessage));
  }

  static success(message: string, options: LogOptions = {}): void {
    const formattedMessage = this.formatMessage(message, {
      ...options,
      level: LogLevel.SUCCESS,
    });
    console.log(colors.green(formattedMessage));
  }

  static custom(
    message: string,
    color: keyof Colors,
    options: LogOptions = {}
  ): void {
    const formattedMessage = this.formatMessage(message, options);
    if (typeof colors[color] !== "boolean") {
      console.log(colors[color](formattedMessage));
      return;
    }
  }
}

// Type definition for available colors
type Colors = typeof colors;

export default Logger;

// Usage examples:
/*
Logger.debug('Debug message', { timestamp: true, prefix: 'APP' });
Logger.info('Info message', { prefix: 'SERVER' });
Logger.warn('Warning message');
Logger.error('Error message', { timestamp: true });
Logger.success('Success message', { prefix: 'DB' });
Logger.custom('Custom colored message', 'magenta', { prefix: 'CUSTOM' });
*/
