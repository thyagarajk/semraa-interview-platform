import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { semraaHttpInterceptor } from './semraa-http.interceptor';

describe('semraaHttpInterceptor', () => {
  let http: HttpClient;
  let controller: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([semraaHttpInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    controller = TestBed.inject(HttpTestingController);
  });

  it('adds a correlation id but no idempotency key to GET', () => {
    http.get('/api/v1/x').subscribe();
    const req = controller.expectOne('/api/v1/x');
    expect(req.request.headers.has('X-Correlation-Id')).toBe(true);
    expect(req.request.headers.has('Idempotency-Key')).toBe(false);
  });

  it('adds an idempotency key to POST', () => {
    http.post('/api/v1/x', {}).subscribe();
    const req = controller.expectOne('/api/v1/x');
    expect(req.request.headers.has('Idempotency-Key')).toBe(true);
  });
});
