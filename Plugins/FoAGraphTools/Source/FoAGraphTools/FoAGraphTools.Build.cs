using UnrealBuildTool;

public class FoAGraphTools : ModuleRules
{
	public FoAGraphTools(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine" });
		PrivateDependencyModuleNames.AddRange(new[]
		{
			"Slate", "SlateCore", "RenderCore", "UnrealEd", "Kismet", "GraphEditor", "UMG", "UMGEditor"
		});
	}
}
