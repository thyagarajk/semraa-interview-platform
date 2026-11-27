using System.Security.Claims;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Semraa.Identity.Contracts;
using Semraa.SharedKernel;

namespace Semraa.Identity;

public sealed class IdentityModule : IModule
{
    public static string Name => "identity";

    public static void AddServices(IServiceCollection services, IConfiguration configuration)
    {
        // Keycloak user/role sync and membership lookups arrive in M2.
    }
}

public static class IdentityEndpoints
{
    public static IEndpointRouteBuilder MapIdentityEndpoints(this IEndpointRouteBuilder app)
    {
        ArgumentNullException.ThrowIfNull(app);
        var group = app.MapGroup("/api/v1/identity").WithTags("Identity");

        group.MapGet("/me", GetCurrentUser)
            .RequireAuthorization()
            .WithName("GetCurrentUser");

        return app;
    }

    private static IResult GetCurrentUser(ClaimsPrincipal user)
    {
        var subject = user.FindFirstValue(ClaimTypes.NameIdentifier) ?? user.FindFirstValue("sub");
        if (!Guid.TryParse(subject, out var userId))
        {
            return TypedResults.Problem(statusCode: StatusCodes.Status401Unauthorized, title: "Invalid subject.");
        }

        var roles = user.FindAll(ClaimTypes.Role).Select(c => c.Value).ToArray();
        return TypedResults.Ok(new CurrentUserResponse(userId, user.FindFirstValue("name"), roles));
    }
}
