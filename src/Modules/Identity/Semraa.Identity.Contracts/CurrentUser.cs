namespace Semraa.Identity.Contracts;

/// <summary>Public view of the signed-in user. No personal data beyond what the caller already owns.</summary>
public sealed record CurrentUserResponse(Guid UserId, string? DisplayName, IReadOnlyList<string> Roles);
