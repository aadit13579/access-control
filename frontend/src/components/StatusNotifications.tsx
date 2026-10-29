import { InlineNotification } from '@carbon/react';

type Props = {
  error: string | null;
  success: string | null;
  errorStyle?: React.CSSProperties;
  successStyle?: React.CSSProperties;
};

/**
 * Renders error and/or success inline notifications.
 */
export function StatusNotifications({
  error,
  success,
  errorStyle,
  successStyle,
}: Props) {
  return (
    <>
      {error && (
        <div style={errorStyle ?? { marginTop: '1rem' }}>
          <InlineNotification kind="error" title="Error" subtitle={error} />
        </div>
      )}

      {success && (
        <div style={successStyle ?? { marginTop: '1rem' }}>
          <InlineNotification
            kind="success"
            title="Success"
            subtitle={success}
          />
        </div>
      )}
    </>
  );
}

