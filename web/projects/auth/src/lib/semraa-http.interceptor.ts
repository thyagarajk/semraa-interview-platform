import { HttpInterceptorFn } from '@angular/common/http';

const STATE_CHANGING = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

/**
 * The one HTTP interceptor (Engineering Standards 6): adds a correlation id to every call and an
 * idempotency key to every state-changing call. Auth tokens are added here in M2 (BFF or in-memory only).
 * It never logs request bodies.
 */
export const semraaHttpInterceptor: HttpInterceptorFn = (req, next) => {
  const headers: Record<string, string> = { 'X-Correlation-Id': crypto.randomUUID() };
  if (STATE_CHANGING.has(req.method) && !req.headers.has('Idempotency-Key')) {
    headers['Idempotency-Key'] = crypto.randomUUID();
  }
  return next(req.clone({ setHeaders: headers }));
};
