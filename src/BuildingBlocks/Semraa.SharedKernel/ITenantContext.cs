namespace Semraa.SharedKernel;

/// <summary>
/// The tenant for the current request. Resolved server-side from the token and the membership table,
/// never from a header or route value alone.
/// </summary>
public interface ITenantContext
{
    /// <summary>Null for B2C users (owner scope is the user) and for platform staff outside a tenant.</summary>
    TenantId? TenantId { get; }

    UserId? UserId { get; }

    bool IsResolved { get; }
}
