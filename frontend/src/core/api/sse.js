// In other words: opens the live progress stream and calls your functions when events arrive.
// Returns a function that closes the stream.
export function openStream(url, { onStage, onCompleted, onError }) {
  const es = new EventSource(url);
  es.addEventListener('stage', (m) => onStage(JSON.parse(m.data)));
  es.addEventListener('completed', (m) => { onCompleted(JSON.parse(m.data)); es.close(); });
  es.addEventListener('error', (m) => {
    // Backend "error" events carry a message; a dropped connection does not.
    const msg = m && m.data ? JSON.parse(m.data).message : 'Connection to the API was lost.';
    onError(msg); es.close();
  });
  return () => es.close();
}
