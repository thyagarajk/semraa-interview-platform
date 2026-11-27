namespace Semraa.SharedKernel;

/// <summary>Strongly typed tenant id. Raw Guids are not passed around for tenants.</summary>
public readonly record struct TenantId(Guid Value)
{
    public static TenantId New() => new(Guid.CreateVersion7());

    public override string ToString() => Value.ToString();
}

/// <summary>Strongly typed user id (one global user across apps and tenants).</summary>
public readonly record struct UserId(Guid Value)
{
    public static UserId New() => new(Guid.CreateVersion7());

    public override string ToString() => Value.ToString();
}
