namespace Semraa.Tenancy.Contracts;

/// <summary>Capabilities that can be chosen per tenant at runtime (architecture doc 5.16).</summary>
public enum ProviderCapability
{
    Llm,
    SpeechToText,
    TextToSpeech,
    ObjectStorage,
    Email,
    Sms,
    PaymentGateway,
    IdentityFederation,
}

/// <summary>
/// Which adapter a tenant uses for a capability. Holds a secret reference (vault key), never the secret.
/// </summary>
public sealed record TenantProviderSetting(
    Guid TenantId,
    ProviderCapability Capability,
    string ProviderKey,
    IReadOnlyDictionary<string, string> Settings,
    string? SecretReference);
