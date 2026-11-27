import { InjectionToken } from '@angular/core';

/** Base URL of the Semraa API. The typed client is generated from the OpenAPI spec in M2. */
export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL', {
  factory: () => '/api/v1',
});
