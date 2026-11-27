using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace Semraa.SharedKernel;

/// <summary>Each module registers its own services. Endpoints are mapped by the host through the module's own extension.</summary>
public interface IModule
{
    static abstract string Name { get; }

    static abstract void AddServices(IServiceCollection services, IConfiguration configuration);
}
