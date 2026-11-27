using Semraa.SharedKernel;

namespace Semraa.SharedKernel.Tests;

public sealed class ResultTests
{
    [Fact]
    public void Success_exposes_value()
    {
        var result = Result.Success(42);

        Assert.True(result.IsSuccess);
        Assert.Equal(42, result.Value);
    }

    [Fact]
    public void Failure_throws_on_value_access()
    {
        var result = Result.Failure<int>(DomainError.NotFound("campaign.not_found", "Campaign not found."));

        Assert.False(result.IsSuccess);
        Assert.Equal(ErrorKind.NotFound, result.Error!.Kind);
        Assert.Throws<InvalidOperationException>(() => result.Value);
    }

    [Fact]
    public void New_tenant_ids_are_version_7()
    {
        Assert.Equal(7, TenantId.New().Value.Version);
    }
}
