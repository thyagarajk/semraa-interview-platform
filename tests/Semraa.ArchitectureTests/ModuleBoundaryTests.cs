using System.Reflection;
using NetArchTest.Rules;

namespace Semraa.ArchitectureTests;

/// <summary>Modules talk only through Contracts projects (Engineering Standards, section 3).</summary>
public sealed class ModuleBoundaryTests
{
    private static readonly string[] Modules = ["Identity", "Tenancy"];

    private static readonly string[] ImplementationAssemblies = ["Semraa.SharedKernel", "Semraa.Identity", "Semraa.Tenancy"];

    public static TheoryData<string, string> ModulePairs()
    {
        var data = new TheoryData<string, string>();
        foreach (var from in Modules)
        {
            foreach (var to in Modules.Where(m => m != from))
            {
                data.Add(from, to);
            }
        }

        return data;
    }

    [Theory]
    [MemberData(nameof(ModulePairs))]
    public void Module_does_not_reference_another_modules_implementation(string from, string to)
    {
        var references = Assembly.Load($"Semraa.{from}")
            .GetReferencedAssemblies()
            .Select(a => a.Name);

        Assert.DoesNotContain($"Semraa.{to}", references);
    }

    [Theory]
    [InlineData("Identity")]
    [InlineData("Tenancy")]
    public void Contracts_do_not_reference_any_module_implementation(string module)
    {
        var references = Assembly.Load($"Semraa.{module}.Contracts")
            .GetReferencedAssemblies()
            .Select(a => a.Name)
            .ToArray();

        foreach (var other in Modules)
        {
            Assert.DoesNotContain($"Semraa.{other}", references);
        }
    }

    [Fact]
    public void Shared_kernel_does_not_depend_on_modules()
    {
        var result = Types.InAssembly(Assembly.Load("Semraa.SharedKernel"))
            .ShouldNot()
            .HaveDependencyOnAny([.. Modules.Select(m => $"Semraa.{m}")])
            .GetResult();

        Assert.True(result.IsSuccessful, string.Join(", ", result.FailingTypeNames ?? []));
    }

    [Fact]
    public void Classes_are_sealed_or_abstract_or_static()
    {
        var assemblies = ImplementationAssemblies.Select(Assembly.Load);
        var unsealed = assemblies
            .SelectMany(a => a.GetTypes())
            .Where(t => t.IsClass && !t.IsSealed && !t.IsAbstract && !t.Name.StartsWith('<'))
            .Select(t => t.FullName)
            .ToArray();

        Assert.Empty(unsealed);
    }
}
