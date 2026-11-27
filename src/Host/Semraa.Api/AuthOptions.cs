namespace Semraa.Api;

internal sealed class AuthOptions
{
    public const string Section = "Auth";

    /// <summary>Keycloak realm URL, e.g. http://localhost:8080/realms/semraa.</summary>
    public string Authority { get; init; } = "http://localhost:8080/realms/semraa";

    public string Audience { get; init; } = "semraa-api";
}
