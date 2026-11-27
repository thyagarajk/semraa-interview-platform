namespace Semraa.Api;

internal static class SecurityHeaders
{
    /// <summary>Baseline headers for an API that serves only JSON.</summary>
    public static IApplicationBuilder UseSecurityHeaders(this IApplicationBuilder app) =>
        app.Use(async (context, next) =>
        {
            var headers = context.Response.Headers;
            headers.XContentTypeOptions = "nosniff";
            headers.XFrameOptions = "DENY";
            headers["Referrer-Policy"] = "no-referrer";
            headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()";
            headers.ContentSecurityPolicy = "default-src 'none'; frame-ancestors 'none'";
            await next(context).ConfigureAwait(false);
        });
}
