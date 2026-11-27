using System.Security.Claims;
using Microsoft.AspNetCore.Http;
using Semraa.SharedKernel;

namespace Semraa.Tenancy;

/// <summary>
/// Scoped tenant context. M0 resolves only the user id from the validated token; the tenant is resolved
/// from the membership table in M2. It is never taken from a header or route value.
/// </summary>
internal sealed class RequestTenantContext(IHttpContextAccessor accessor) : ITenantContext
{
    private readonly Lazy<UserId?> _userId = new(() =>
    {
        var user = accessor.HttpContext?.User;
        var subject = user?.FindFirstValue(ClaimTypes.NameIdentifier) ?? user?.FindFirstValue("sub");
        return Guid.TryParse(subject, out var id) ? new UserId(id) : null;
    });

    public TenantId? TenantId => null;

    public UserId? UserId => _userId.Value;

    public bool IsResolved => UserId is not null;
}
