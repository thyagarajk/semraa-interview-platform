namespace Semraa.SharedKernel;

/// <summary>An expected failure (validation, not found, insufficient credits). Exceptions are for the unexpected.</summary>
public sealed record DomainError(string Code, string Message, ErrorKind Kind = ErrorKind.Failure)
{
    public static DomainError NotFound(string code, string message) => new(code, message, ErrorKind.NotFound);
    public static DomainError Validation(string code, string message) => new(code, message, ErrorKind.Validation);
    public static DomainError Conflict(string code, string message) => new(code, message, ErrorKind.Conflict);
    public static DomainError Forbidden(string code, string message) => new(code, message, ErrorKind.Forbidden);
}

public enum ErrorKind
{
    Failure,
    Validation,
    NotFound,
    Conflict,
    Forbidden,
}

public sealed class Result<T>
{
    private readonly T? _value;

    private Result(T value)
    {
        _value = value;
        IsSuccess = true;
    }

    private Result(DomainError error)
    {
        Error = error;
        IsSuccess = false;
    }

    public bool IsSuccess { get; }

    public DomainError? Error { get; }

    public T Value => IsSuccess
        ? _value!
        : throw new InvalidOperationException("Cannot read the value of a failed result.");

    internal static Result<T> FromValue(T value) => new(value);

    internal static Result<T> FromError(DomainError error) => new(error);

    public TOut Match<TOut>(Func<T, TOut> onSuccess, Func<DomainError, TOut> onFailure)
    {
        ArgumentNullException.ThrowIfNull(onSuccess);
        ArgumentNullException.ThrowIfNull(onFailure);
        return IsSuccess ? onSuccess(_value!) : onFailure(Error!);
    }
}

public static class Result
{
    public static Result<T> Success<T>(T value) => Result<T>.FromValue(value);

    public static Result<T> Failure<T>(DomainError error)
    {
        ArgumentNullException.ThrowIfNull(error);
        return Result<T>.FromError(error);
    }
}
