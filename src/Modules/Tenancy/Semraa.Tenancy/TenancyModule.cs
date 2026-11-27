using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Semraa.SharedKernel;

namespace Semraa.Tenancy;

public sealed class TenancyModule : IModule
{
    public static string Name => "tenancy";

    public static void AddServices(IServiceCollection services, IConfiguration configuration)
    {
        services.AddHttpContextAccessor();
        services.AddScoped<ITenantContext, RequestTenantContext>();
    }
}
